import os
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from dotenv import load_dotenv

import hashlib

from generators.gemini import GeminiClient
from models import AlphaSignal
from utils.config import load_config
from utils.logger import get_logger
from utils.output_format import format_five_modules_multiline
from utils.run_stats import save_run_stats

load_dotenv()
logger = get_logger(__name__)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

BASE_DIR = os.path.dirname(__file__)
STATE_FILE = os.path.join(BASE_DIR, 'data', 'processed_urls.json')
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
GEN_DIR = os.path.join(BASE_DIR, 'data', 'generated')
CONFIG = load_config(BASE_DIR)
NON_ALPHA_PATTERNS = [
    r"\battend\b",
    r"\bsummit\b",
    r"\bwebinar\b",
    r"\bregister\b",
    r"\bconference\b",
    r"\bcall for\b",
    r"\bevent\b",
    r"\bmeetup\b",
    r"\bapply now\b",
    r"\bhiring\b",
    r"\bjoin us\b",
]


def parse_score(raw_score):
    if raw_score is None:
        return None
    match = re.search(r"(\d+(\.\d+)?)", str(raw_score))
    if not match:
        return None
    return float(match.group(1))


def normalize_alpha_output(text):
    if not text:
        return None
    return format_five_modules_multiline(str(text))


def apply_final_score(alpha_text, score_value):
    if not alpha_text or score_value is None:
        return alpha_text
    return re.sub(
        r"【Alpha评分】:\s*.*",
        f"【Alpha评分】: {score_value:.1f}分",
        alpha_text,
        count=1,
    )


def is_non_alpha_item(item):
    haystack = " ".join([
        str(item.get("source", "")),
        str(item.get("title", "")),
        str(item.get("summary", ""))[:500],
    ]).lower()
    for pattern in NON_ALPHA_PATTERNS:
        if re.search(pattern, haystack, re.IGNORECASE):
            return True
    return False

def load_processed_urls():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            try:
                return set(json.load(f))
            except Exception as e:
                logger.error(f"Failed to read state file: {e}")
    return set()

def save_processed_urls(url_set):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp_file = STATE_FILE + '.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(list(url_set), f, ensure_ascii=False)
    os.replace(tmp_file, STATE_FILE)

def get_unprocessed_items(processed_set):
    items = []
    # Read today and yesterday
    for days_back in [0, 1]:
        date_str = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        day_dir = os.path.join(RAW_DIR, date_str)
        if not os.path.exists(day_dir):
            continue
        
        for filename in os.listdir(day_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(day_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for item in data:
                            if item.get('url') not in processed_set:
                                items.append(item)
                except Exception as e:
                    logger.error(f"Failed to read raw file {filename}: {e}")
    
    unique_items = []
    seen = set()
    for item in items:
        url = item.get('url')
        if url and url not in seen:
            seen.add(url)
            unique_items.append(item)
            
    return unique_items

def detect_source_lang(item: dict) -> str:
    """Heuristic: if the summary contains any CJK code points, treat the
    source as Chinese; otherwise English. Cheap, correct for our sources
    (English RSS + arXiv ≫ Chinese RSS so far)."""
    blob = (item.get("title") or "") + " " + (item.get("summary") or "")
    for ch in blob:
        if "一" <= ch <= "鿿":
            return "zh"
    return "en"


def _signal_id_for(item: dict) -> str:
    url = item.get("url") or ""
    title = item.get("title") or ""
    return hashlib.sha256((url or title).encode("utf-8")).hexdigest()[:16]


def save_generated_alpha(item, alpha_content, *, lang: str, score: float):
    """Persist the generated signal as an ``AlphaSignal`` JSON artifact.

    A sibling ``.md`` is also written for human inspection / legacy tooling
    that still reads the markdown directly. The JSON form is what the
    orchestrator prefers (it carries source_lang and tier metadata that the
    markdown alone cannot express).
    """
    today = datetime.now().strftime('%Y-%m-%d')
    day_dir = os.path.join(GEN_DIR, today)
    os.makedirs(day_dir, exist_ok=True)

    safe_title = "".join([c if c.isalnum() else "_" for c in item['title'][:30]])
    stem = os.path.join(day_dir, f"{safe_title}_{int(time.time())}")

    # Human-readable copy (preserves backward compatibility).
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(alpha_content)

    # Canonical artifact.
    sig = AlphaSignal(
        id=_signal_id_for(item),
        source_url=item.get("url") or "",
        source_lang=lang,
        source=item.get("source") or "",
        title=item.get("title") or "",
        score=float(score),
        tier="free",
        bodies={lang: alpha_content},
        paid_only_fields={"source_url": item.get("url") or ""} if item.get("url") else {},
    )
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(sig.to_dict(), f, ensure_ascii=False, indent=2)


def process_item(item, min_alpha_score, generation_cfg):
    url = item.get("url")
    data_summary = f"Source: {item['source']}\nTitle: {item['title']}\nSummary: {item['summary']}\nURL: {url}"
    gemini = GeminiClient(api_key=GEMINI_KEY, generation_config=generation_cfg)

    score_raw = gemini.score_alpha(data_summary)
    score_value = parse_score(score_raw)
    if score_value is None:
        return {"status": "score_parse_failed", "item": item}
    if score_value < min_alpha_score:
        return {"status": "skipped_by_score", "item": item, "score_value": score_value}

    source_lang = detect_source_lang(item)
    alpha_content = gemini.generate_alpha(data_summary, lang=source_lang)
    if not alpha_content:
        return {"status": "generation_failed", "item": item, "score_value": score_value}

    normalized_content = normalize_alpha_output(alpha_content)
    if not normalized_content:
        return {"status": "normalize_failed", "item": item, "score_value": score_value}

    normalized_content = apply_final_score(normalized_content, score_value)
    return {
        "status": "processed",
        "item": item,
        "score_value": score_value,
        "content": normalized_content,
        "lang": source_lang,
    }

def run_ais_generate():
    logger.info("Starting AIS Generation Module (2-Hour Cycle)...")
    score_cfg = CONFIG.get("scoring", {})
    generation_cfg = CONFIG.get("generation", {})
    min_alpha_score = float(score_cfg.get("min_alpha_score", 0.0))
    max_items = int(score_cfg.get("max_items_per_cycle", 10))
    worker_count = max(1, int(generation_cfg.get("worker_count", 2)))
    
    processed_urls = load_processed_urls()
    items_to_process = get_unprocessed_items(processed_urls)
    
    if not items_to_process:
        logger.info("No new unprocessed items. Exiting.")
        stats = {
            "success": True,
            "total_candidates": 0,
            "attempted": 0,
            "processed": 0,
            "skipped_by_score": 0,
            "skipped_non_alpha": 0,
            "score_parse_failed": 0,
            "generation_failed": 0,
            "normalize_failed": 0,
            "min_alpha_score": min_alpha_score,
            "max_items_per_cycle": max_items,
        }
        save_run_stats(BASE_DIR, "generate", stats)
        return stats
        
    logger.info(f"Found {len(items_to_process)} new items. Connecting to Gemini...")

    newly_processed = 0
    skipped_by_score = 0
    skipped_non_alpha = 0
    score_parse_failed = 0
    generation_failed = 0
    normalize_failed = 0
    work_items = []
    for item in items_to_process[:max_items]:
        url = item.get('url')
        logger.info(f"Queueing Alpha generation for: [{item['source']}] {item['title'][:50]}...")

        if is_non_alpha_item(item):
            skipped_non_alpha += 1
            logger.info(f"Skipped non-alpha item by heuristic filter: [{item['source']}] {item['title'][:50]}")
            if url:
                processed_urls.add(url)
                save_processed_urls(processed_urls)
            continue

        work_items.append(item)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(process_item, item, min_alpha_score, generation_cfg): item
            for item in work_items
        }
        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.error(f"Unhandled generation worker error for [{item['source']}]: {e}")
                generation_failed += 1
                continue

            url = item.get("url")

            if result["status"] == "score_parse_failed":
                logger.warning(f"Could not parse alpha score for [{item['source']}], skipping this cycle.")
                score_parse_failed += 1
                continue
            if result["status"] == "skipped_by_score":
                skipped_by_score += 1
                logger.info(
                    f"Skipped low-score item ({result['score_value']:.1f} < {min_alpha_score:.1f})."
                )
                if url:
                    processed_urls.add(url)
                    save_processed_urls(processed_urls)
                continue
            if result["status"] == "generation_failed":
                logger.warning(f"Generation failed for [{item['source']}]. Will retry next cycle.")
                generation_failed += 1
                continue
            if result["status"] == "normalize_failed":
                logger.warning(f"Generated empty content after normalization for [{item['source']}].")
                normalize_failed += 1
                continue

            save_generated_alpha(
                item,
                result["content"],
                lang=result.get("lang", "zh"),
                score=result.get("score_value", 0.0),
            )
            if url:
                processed_urls.add(url)
                save_processed_urls(processed_urls)
            newly_processed += 1
            logger.info(f"Content saved to generated directory for [{item['source']}].")

    save_processed_urls(processed_urls)
    logger.info(
        f"Generation cycle completed. Processed {newly_processed} items, "
        f"skipped {skipped_by_score} by score threshold ({min_alpha_score:.1f})."
    )
    stats = {
        "success": True,
        "total_candidates": len(items_to_process),
        "attempted": min(len(items_to_process), max_items),
        "processed": newly_processed,
        "skipped_by_score": skipped_by_score,
        "skipped_non_alpha": skipped_non_alpha,
        "score_parse_failed": score_parse_failed,
        "generation_failed": generation_failed,
        "normalize_failed": normalize_failed,
        "min_alpha_score": min_alpha_score,
        "max_items_per_cycle": max_items,
    }
    save_run_stats(BASE_DIR, "generate", stats)
    return stats

if __name__ == "__main__":
    if not GEMINI_KEY:
        logger.error("Missing GEMINI_API_KEY in .env file.")
    else:
        run_ais_generate()
