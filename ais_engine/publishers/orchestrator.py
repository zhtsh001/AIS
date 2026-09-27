"""Publish-cycle orchestrator.

Responsibilities:
1. Load generated signals for the cycle window (today for daily, last 7 days
   for weekly). Backwards compatible with the legacy ``.md`` artifact format
   (``data/generated/{date}/*.md`` produced by the current ``generate.py``);
   also forwards-compatible with the new ``.json`` artifacts that Phase 3
   will emit.
2. Deduplicate by source URL and content hash (carried over from the legacy
   ``publish.split_batches`` path).
3. Apply compliance filter (``processors.compliance.safety_filter``).
4. Filter subscribers by tier eligibility.
5. Ensure each ``signal.bodies[subscriber.lang]`` is populated (Phase 3:
   call ``i18n.translator``).
6. Group subscribers by channel and dispatch to the corresponding
   ``BasePublisher``.
7. Record per-subscriber outcomes via the deliveries table (Phase 2+).

Phase 1 behavior: subscribers store is empty, so the orchestrator falls back
to a "local archive" mode that mirrors the legacy ``publish.py`` output —
batched plaintext files dropped into ``test_outputs/``. This keeps cron from
breaking the day Phase 1 lands.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
from datetime import datetime, timedelta
from typing import Optional

from i18n.translator import Translator
from models import AlphaSignal, Subscriber
from processors.compliance import safety_filter
from publishers.base import BasePublisher, DeliveryResult
from publishers.renderers.plaintext import DEFAULT_SEPARATOR, PlaintextRenderer
from subscribers import store as subs_store
from utils.config import load_config
from utils.logger import get_logger
from utils.output_format import format_five_modules_multiline
from utils.run_stats import load_latest_stats, save_run_stats
from utils.schedule_guard import already_ran_today, is_bj_time_in_window, mark_ran_today

logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
GEN_DIR = os.path.join(BASE_DIR, "data", "generated")
TEST_OUTPUTS = os.path.join(BASE_DIR, "test_outputs")


# --------------------------------------------------------------------------- #
# Signal loading (legacy .md + future .json artifacts)
# --------------------------------------------------------------------------- #

def _extract_source_link(text: str) -> Optional[str]:
    match = re.search(r"【信源链接】:\s*(\S+)", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"\[Source\]:\s*(\S+)", text)
    return match.group(1).strip() if match else None


def _signal_from_legacy_md(path: str) -> Optional[AlphaSignal]:
    """Lift a legacy ``data/generated/{date}/*.md`` blob into an AlphaSignal.

    The legacy artifact is a single normalized 5-module Chinese string.
    We treat it as ``source_lang="zh"`` with body keyed accordingly.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        logger.error(f"Failed to read legacy artifact {path}: {e}")
        return None

    text = format_five_modules_multiline(raw).strip()
    if not text:
        return None

    cleaned = safety_filter(text)
    if cleaned is None:
        logger.warning(f"Dropped {path} due to compliance filter.")
        return None

    source_url = _extract_source_link(cleaned) or ""
    sid = hashlib.sha256((source_url or cleaned).encode("utf-8")).hexdigest()[:16]
    return AlphaSignal(
        id=sid,
        source_url=source_url,
        source_lang="zh",
        title=os.path.basename(path),
        bodies={"zh": cleaned},
        paid_only_fields={"source_url": source_url} if source_url else {},
    )


def _signal_from_json(path: str) -> Optional[AlphaSignal]:
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read JSON artifact {path}: {e}")
        return None

    try:
        sig = AlphaSignal.from_dict(data)
    except Exception as e:
        logger.error(f"Malformed AlphaSignal JSON at {path}: {e}")
        return None

    # Apply compliance to every body to be safe.
    for lang, body in list(sig.bodies.items()):
        cleaned = safety_filter(body)
        if cleaned is None:
            sig.bodies.pop(lang)
    if not sig.bodies:
        logger.warning(f"All bodies of {path} dropped by compliance filter.")
        return None
    return sig


def _load_signals_for_dates(dates: list[str]) -> list[AlphaSignal]:
    signals: list[AlphaSignal] = []
    seen_urls: set[str] = set()
    seen_hashes: set[str] = set()
    dropped_dupes = 0

    for date_str in dates:
        day_dir = os.path.join(GEN_DIR, date_str)
        if not os.path.isdir(day_dir):
            continue
        for filename in sorted(os.listdir(day_dir)):
            path = os.path.join(day_dir, filename)
            if filename.endswith(".json"):
                sig = _signal_from_json(path)
            elif filename.endswith(".md"):
                sig = _signal_from_legacy_md(path)
            else:
                continue
            if sig is None:
                continue

            # Dedup by source URL across the cycle window.
            if sig.source_url and sig.source_url in seen_urls:
                dropped_dupes += 1
                continue

            # Dedup by content hash (catch identical bodies w/o URL).
            content_blob = "\n".join(sig.bodies.values())
            chash = hashlib.sha256(content_blob.encode("utf-8")).hexdigest()
            if chash in seen_hashes:
                dropped_dupes += 1
                continue

            if sig.source_url:
                seen_urls.add(sig.source_url)
            seen_hashes.add(chash)
            signals.append(sig)

    if dropped_dupes:
        logger.info(f"Orchestrator deduplicated {dropped_dupes} signals during load.")
    return signals


# --------------------------------------------------------------------------- #
# Local archive (Phase 1 fallback when subscribers store is empty)
# --------------------------------------------------------------------------- #

def _archive_locally(signals: list[AlphaSignal], label: str, byte_limit: int) -> list[str]:
    """Write a plaintext zh batch to ``test_outputs/`` — mirrors legacy publish.py.

    Used when there are no subscribers yet (Phase 1) or whenever the caller
    passes ``--dry-run``.
    """
    if not signals:
        return []
    os.makedirs(TEST_OUTPUTS, exist_ok=True)

    renderer = PlaintextRenderer(max_bytes=byte_limit, separator=DEFAULT_SEPARATOR)
    # Synthetic "subscriber" so the renderer picks the zh body.
    from models import Subscriber
    fake = Subscriber(id="local", channel="rss", address="local", langs=["zh"])

    batches = renderer.render(signals, fake)
    if not batches:
        return []

    ts = int(time.time())
    today = datetime.now().strftime("%Y-%m-%d")
    out_files: list[str] = []
    for idx, content in enumerate(batches, start=1):
        out = os.path.join(TEST_OUTPUTS, f"AIS_{label}_Digest_{today}_{ts}_part{idx}.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        out_files.append(out)
        logger.info(f"Archived batch {idx}/{len(batches)} to {out}")
    return out_files


# --------------------------------------------------------------------------- #
# Subscriber-driven dispatch (Phase 2+)
# --------------------------------------------------------------------------- #

def _build_publisher(channel: str, cfg: dict) -> BasePublisher | None:
    """Instantiate the Publisher for ``channel`` if it's enabled and the
    required env credentials exist. Returns ``None`` to silently skip.

    Keeping construction local (rather than a module-level registry) means a
    missing credential disables one channel without crashing the whole run.
    """
    pub_cfg = (cfg.get("publishers") or {}).get(channel) or {}
    if not pub_cfg.get("enabled"):
        return None

    if channel == "telegram":
        token_env = pub_cfg.get("bot_token_env", "TELEGRAM_BOT_TOKEN")
        token = os.environ.get(token_env)
        if not token:
            logger.warning(f"Telegram disabled: env {token_env} not set.")
            return None
        from publishers.telegram import TelegramPublisher
        return TelegramPublisher(
            bot_token=token,
            max_chars=int(pub_cfg.get("max_chars", 4096)),
        )

    if channel == "email":
        from_env = pub_cfg.get("from_env", "AIS_EMAIL_FROM")
        sender = os.environ.get(from_env)
        if not sender:
            logger.warning(f"Email disabled: env {from_env} not set.")
            return None
        transport = pub_cfg.get("transport", "resend")
        api_key_env = pub_cfg.get("api_key_env", "RESEND_API_KEY")
        api_key = os.environ.get(api_key_env)
        if transport == "resend" and not api_key:
            logger.warning(f"Email disabled: env {api_key_env} not set for resend transport.")
            return None
        from publishers.email import EmailPublisher
        public_origin = os.environ.get(
            "AIS_PUBLIC_ORIGIN",
            (cfg.get("subscribe_server") or {}).get("public_origin"),
        )
        return EmailPublisher(
            sender=sender,
            transport=transport,
            api_key=api_key,
            public_origin=public_origin,
        )

    logger.warning(f"Unknown channel '{channel}' in config; skipping.")
    return None


def _eligible_signals_for(subscriber: Subscriber, signals: list[AlphaSignal]) -> list[AlphaSignal]:
    """Apply tier gating + per-subscriber dedupe (deliveries idempotency)."""
    cfg = load_config(BASE_DIR)
    db_path = _db_path(cfg)

    pool = [s for s in signals if _tier_allows(s, subscriber)]
    if not pool:
        return []

    candidate_ids = [s.id for s in pool]
    undelivered_ids = set(
        subs_store.filter_undelivered(db_path, candidate_ids, subscriber.id)
    )
    return [s for s in pool if s.id in undelivered_ids]


def _tier_allows(signal: AlphaSignal, subscriber: Subscriber) -> bool:
    """Free subscribers see free-tier signals; paid see all."""
    if subscriber.tier == "paid":
        return True
    return signal.tier == "free"


def _db_path(cfg: dict) -> str:
    rel = (cfg.get("subscribers") or {}).get("db_path", "data/subscribers.db")
    return os.path.join(BASE_DIR, rel)


def _build_translator(cfg: dict) -> Translator | None:
    """Build the Translator if GEMINI_API_KEY is available; otherwise return
    ``None`` so the orchestrator skips on-demand translation (renderer will
    fall back to source_lang body)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    from generators.gemini import GeminiClient

    i18n_cfg = cfg.get("i18n") or {}
    cache_rel = i18n_cfg.get("translation_cache_dir", "data/translations")
    cache_abs = os.path.join(BASE_DIR, cache_rel)
    generation_cfg = cfg.get("generation") or {}
    client = GeminiClient(api_key=api_key, generation_config=generation_cfg)
    return Translator(client=client, cache_dir=cache_abs)


def _dispatch_to_publishers(signals: list[AlphaSignal], dry_run: bool) -> dict:
    """Load subscribers, group by channel, dispatch via the right Publisher.

    Returns a summary the orchestrator merges into its run-stats. Falls back
    to ``dispatched == 0`` (so the local-archive path kicks in) when there
    are no active subscribers OR no enabled Publisher matches.
    """
    cfg = load_config(BASE_DIR)
    db_path = _db_path(cfg)
    if not os.path.exists(db_path):
        return {"dispatched": 0, "publishers": [], "results": []}

    subs = subs_store.list_active(db_path)
    if not subs:
        return {"dispatched": 0, "publishers": [], "results": []}

    by_channel: dict[str, list[Subscriber]] = {}
    for s in subs:
        by_channel.setdefault(s.channel, []).append(s)

    summary: list[dict] = []
    all_results: list[DeliveryResult] = []
    dispatched = 0

    for channel, channel_subs in by_channel.items():
        publisher = _build_publisher(channel, cfg)
        if publisher is None:
            summary.append({"channel": channel, "subscribers": len(channel_subs), "skipped": True})
            continue

        # Per-subscriber tier + undelivered filtering.
        translator = _build_translator(cfg)
        for sub in channel_subs:
            eligible = _eligible_signals_for(sub, signals)
            if not eligible:
                continue
            # Ensure each eligible signal has a body in the subscriber's lang.
            # Missing translations on cache miss + no LLM client are tolerated:
            # the renderer falls back to source_lang via AlphaSignal.body_for().
            if translator is not None:
                for sig in eligible:
                    if sub.lang not in sig.bodies:
                        translator.ensure(sig, sub.lang)
            results = publisher.publish([*eligible], [sub], dry_run=dry_run)
            all_results.extend(results)
            for r in results:
                if r.success and not dry_run:
                    for sid in r.signal_ids:
                        subs_store.mark_delivered(db_path, sid, r.subscriber_id, "ok")
                elif not r.success:
                    logger.error(f"Delivery failed for {r.subscriber_id}: {r.error}")
            dispatched += sum(1 for r in results if r.success)

        summary.append({"channel": channel, "subscribers": len(channel_subs), "skipped": False})

    return {"dispatched": dispatched, "publishers": summary, "results": all_results}


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #

def _bj_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _last_n_days(n: int) -> list[str]:
    today = datetime.now()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]


def run_daily_publish(*, scheduled: bool = False, dry_run: bool = False) -> dict:
    if scheduled:
        if not is_bj_time_in_window(8, 8, window_minutes=5):
            logger.info("Scheduled daily publish skipped: outside BJ 08:08-08:12 window.")
            return {"skipped": "outside_window"}
        if already_ran_today("daily_publish"):
            logger.info("Scheduled daily publish skipped: already ran today.")
            return {"skipped": "already_ran"}

    cfg = load_config(BASE_DIR)
    byte_limit = int(cfg.get("delivery", {}).get("batch_byte_limit", 1800))

    signals = _load_signals_for_dates([_bj_today_str()])
    logger.info(f"Daily publish loaded {len(signals)} eligible signals.")

    dispatch = _dispatch_to_publishers(signals, dry_run=dry_run)
    local_files = _archive_locally(signals, label="Daily", byte_limit=byte_limit) if dispatch["dispatched"] == 0 else []

    stats = {
        "success": True,
        "cycle": "daily",
        "signals": len(signals),
        "dispatched": dispatch["dispatched"],
        "publishers": dispatch["publishers"],
        "local_files": local_files,
        "dry_run": dry_run,
    }
    save_run_stats(BASE_DIR, "publish_daily", stats)
    _write_run_report("daily", _bj_today_str(), stats)

    if scheduled:
        mark_ran_today("daily_publish")
    return stats


def run_weekly_publish(*, scheduled: bool = False, dry_run: bool = False) -> dict:
    if scheduled:
        # Friday (weekday=4) 20:08-20:12 BJ
        if not is_bj_time_in_window(20, 8, window_minutes=5, weekday=4):
            logger.info("Scheduled weekly publish skipped: outside BJ Fri 20:08-20:12.")
            return {"skipped": "outside_window"}
        if already_ran_today("weekly_publish"):
            logger.info("Scheduled weekly publish skipped: already ran today.")
            return {"skipped": "already_ran"}

    cfg = load_config(BASE_DIR)
    byte_limit = int(cfg.get("delivery", {}).get("batch_byte_limit", 1800))

    signals = _load_signals_for_dates(_last_n_days(7))
    logger.info(f"Weekly publish loaded {len(signals)} eligible signals.")

    dispatch = _dispatch_to_publishers(signals, dry_run=dry_run)
    local_files = _archive_locally(signals, label="Weekly", byte_limit=byte_limit) if dispatch["dispatched"] == 0 else []

    stats = {
        "success": True,
        "cycle": "weekly",
        "signals": len(signals),
        "dispatched": dispatch["dispatched"],
        "publishers": dispatch["publishers"],
        "local_files": local_files,
        "dry_run": dry_run,
    }
    save_run_stats(BASE_DIR, "publish_weekly", stats)
    _write_run_report("weekly", _bj_today_str(), stats)

    if scheduled:
        mark_ran_today("weekly_publish")
    return stats


def _write_run_report(cycle: str, today: str, publish_stats: dict) -> str:
    fetch_stats = load_latest_stats(BASE_DIR, "fetch") or {}
    generate_stats = load_latest_stats(BASE_DIR, "generate") or {}

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(TEST_OUTPUTS, exist_ok=True)
    report_path = os.path.join(TEST_OUTPUTS, f"run_report_{cycle}_{ts}.md")

    lines = [
        f"# AIS Local Run Report ({cycle}, {today})",
        "",
        "## Fetch",
        f"- total_count: {fetch_stats.get('total_count', 'N/A')}",
        f"- arxiv_count: {fetch_stats.get('arxiv_count', 'N/A')}",
        f"- rss_count: {fetch_stats.get('rss_count', 'N/A')}",
        "",
        "## Generate",
        f"- processed: {generate_stats.get('processed', 'N/A')}",
        f"- skipped_by_score: {generate_stats.get('skipped_by_score', 'N/A')}",
        f"- min_alpha_score: {generate_stats.get('min_alpha_score', 'N/A')}",
        "",
        "## Publish",
        f"- signals: {publish_stats.get('signals', 'N/A')}",
        f"- dispatched_via_publishers: {publish_stats.get('dispatched', 'N/A')}",
        f"- dry_run: {publish_stats.get('dry_run', 'N/A')}",
        "",
        "## Output Files",
    ]
    for path in publish_stats.get("local_files", []):
        lines.append(f"- {path}")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return report_path
