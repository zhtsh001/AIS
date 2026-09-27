import argparse
import hashlib
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from processors.wechat import AISCore
from publish import extract_source_link, normalize_generated_text, split_batches
from utils.config import load_config
from utils.logger import get_logger
from utils.schedule_guard import already_ran_today, is_bj_time_in_window, mark_ran_today


load_dotenv()
logger = get_logger(__name__)

BASE_DIR = os.path.dirname(__file__)
GEN_DIR = os.path.join(BASE_DIR, "data", "generated")
TEST_OUTPUTS = os.path.join(BASE_DIR, "test_outputs")
CONFIG = load_config(BASE_DIR)


def _push_enabled() -> bool:
    return os.getenv("WECHAT_PUSH_ENABLED", "0") == "1"


def _env(*keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default


def _build_weekly_batches() -> list[str]:
    delivery_cfg = CONFIG.get("delivery", {})
    separator = str(delivery_cfg.get("separator", "\n━━━━━━━━━━━━━━\n"))
    byte_limit = int(delivery_cfg.get("batch_byte_limit", 1800))

    items = []
    seen_links = set()
    seen_hash = set()

    for days_back in range(0, 7):
        day = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        day_dir = os.path.join(GEN_DIR, day)
        if not os.path.exists(day_dir):
            continue
        for filename in sorted(os.listdir(day_dir)):
            if not filename.endswith(".md"):
                continue
            path = os.path.join(day_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = normalize_generated_text(f.read())
            except Exception as e:
                logger.error(f"Failed to read weekly source file {path}: {e}")
                continue

            link = extract_source_link(text)
            if link and link in seen_links:
                continue
            h = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if h in seen_hash:
                continue

            if link:
                seen_links.add(link)
            seen_hash.add(h)
            items.append(text)

    return split_batches(items, separator, byte_limit)


def _save_weekly_files(batches: list[str]) -> list[str]:
    if not batches:
        return []
    os.makedirs(TEST_OUTPUTS, exist_ok=True)
    ts = int(datetime.now().timestamp())
    out_files = []
    for idx, content in enumerate(batches, start=1):
        path = os.path.join(TEST_OUTPUTS, f"AIS_Weekly_Digest_{ts}_part{idx}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        out_files.append(path)
    return out_files


def _send_files(output_files: list[str]) -> None:
    corp_id = _env("WECHAT_CORP_ID", "WECOM_CORP_ID")
    corp_secret = _env("WECHAT_SECRET", "WECOM_SECRET")
    agent_id = _env("WECHAT_AGENT_ID", "WECOM_AGENT_ID")
    to_users = _env("WECHAT_TO_USERS", "WECOM_USER_ID", default="@all")

    if not corp_id or not corp_secret or not agent_id:
        logger.error("Missing WECHAT_CORP_ID / WECHAT_SECRET / WECHAT_AGENT_ID.")
        return

    core = AISCore(corp_id=corp_id, corp_secret=corp_secret, agent_id=int(agent_id))
    user_ids = [u.strip() for u in to_users.split("|") if u.strip()]

    for path in output_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read weekly digest file for push: {path}, err={e}")
            continue

        resp = core.send_text_with_links(user_ids=user_ids, text=content)
        logger.info(f"WeChat weekly push response: {resp}")


def run_weekly_push(scheduled: bool = False) -> None:
    if scheduled:
        # Friday evening in Beijing: 20:08 (assumption)
        if not is_bj_time_in_window(20, 8, window_minutes=5, weekday=4):
            logger.info("Scheduled weekly push skipped: not in Beijing Friday 20:08-20:12 window.")
            return
        if already_ran_today("weekly_push"):
            logger.info("Scheduled weekly push skipped: already ran today.")
            return

    batches = _build_weekly_batches()
    output_files = _save_weekly_files(batches)
    if not output_files:
        logger.info("No weekly output files to push.")
        if scheduled:
            mark_ran_today("weekly_push")
        return

    logger.info(f"Weekly digest files saved: {output_files}")

    if not _push_enabled():
        logger.info("WECHAT_PUSH_ENABLED != 1, weekly push stays local only.")
        if scheduled:
            mark_ran_today("weekly_push")
        return

    _send_files(output_files)
    if scheduled:
        mark_ran_today("weekly_push")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheduled", action="store_true", help="Only run at configured Beijing time.")
    args = parser.parse_args()
    run_weekly_push(scheduled=args.scheduled)
