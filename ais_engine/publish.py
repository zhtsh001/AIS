import os
import time
import hashlib
import re
from datetime import datetime
from dotenv import load_dotenv

from utils.config import load_config
from utils.logger import get_logger
from utils.output_format import format_five_modules_multiline
from utils.run_stats import load_latest_stats, save_run_stats

load_dotenv()
logger = get_logger(__name__)

BASE_DIR = os.path.dirname(__file__)
GEN_DIR = os.path.join(BASE_DIR, 'data', 'generated')
TEST_OUTPUTS = os.path.join(BASE_DIR, "test_outputs")
CONFIG = load_config(BASE_DIR)


def normalize_generated_text(text):
    return format_five_modules_multiline(str(text))


def extract_source_link(text):
    match = re.search(r"【信源链接】:\s*(\S+)", text)
    return match.group(1).strip() if match else None


def split_batches(items, separator, byte_limit):
    batches = []
    current = ""
    for item in items:
        if not item:
            continue
        candidate = item if not current else f"{current}{separator}{item}"
        if len(candidate.encode("utf-8")) <= byte_limit:
            current = candidate
            continue
        if current:
            batches.append(current)
            current = item
        else:
            # Single long item fallback: keep this one item as one batch.
            batches.append(item)
    if current:
        batches.append(current)
    return batches

def run_ais_publish():
    """
    Compile generated daily insights and split by byte limit into local plain-text batches.
    WeChat publishing is intentionally disabled; outputs are saved locally for verification.
    """
    logger.info("Starting AIS Publishing Module (Daily Cycle)...")

    delivery_cfg = CONFIG.get("delivery", {})
    separator = str(delivery_cfg.get("separator", "\n━━━━━━━━━━━━━━\n"))
    byte_limit = int(delivery_cfg.get("batch_byte_limit", 1800))

    today = datetime.now().strftime('%Y-%m-%d')
    day_dir = os.path.join(GEN_DIR, today)

    if not os.path.exists(day_dir) or not os.listdir(day_dir):
        logger.info(f"No generated content found for today ({today}). Nothing to publish.")
        stats = {
            "success": True,
            "insights": 0,
            "batches": 0,
            "byte_limit": byte_limit,
            "output_files": [],
        }
        save_run_stats(BASE_DIR, "publish", stats)
        report_path = write_run_report(today, stats)
        logger.info(f"Run report saved: {report_path}")
        return stats

    logger.info(f"Found generated content in {day_dir}. Building local digest batches...")

    normalized_items = []
    seen_links = set()
    seen_content_hash = set()
    duplicates_removed = 0

    for filename in sorted(os.listdir(day_dir)):
        if filename.endswith(".md"):
            try:
                with open(os.path.join(day_dir, filename), 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    normalized = normalize_generated_text(content)
                    if normalized:
                        link = extract_source_link(normalized)
                        if link and link in seen_links:
                            duplicates_removed += 1
                            continue

                        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                        if content_hash in seen_content_hash:
                            duplicates_removed += 1
                            continue

                        if link:
                            seen_links.add(link)
                        seen_content_hash.add(content_hash)
                        normalized_items.append(normalized)
            except Exception as e:
                logger.error(f"Error reading file {filename}: {e}")

    if not normalized_items:
        logger.info("No valid markdown files could be read.")
        stats = {
            "success": True,
            "insights": 0,
            "batches": 0,
            "byte_limit": byte_limit,
            "output_files": [],
            "duplicates_removed": duplicates_removed,
        }
        save_run_stats(BASE_DIR, "publish", stats)
        report_path = write_run_report(today, stats)
        logger.info(f"Run report saved: {report_path}")
        return stats

    batches = split_batches(normalized_items, separator, byte_limit)
    if not batches:
        logger.info("No digest batches built after normalization.")
        stats = {
            "success": True,
            "insights": len(normalized_items),
            "batches": 0,
            "byte_limit": byte_limit,
            "output_files": [],
            "duplicates_removed": duplicates_removed,
        }
        save_run_stats(BASE_DIR, "publish", stats)
        report_path = write_run_report(today, stats)
        logger.info(f"Run report saved: {report_path}")
        return stats

    os.makedirs(TEST_OUTPUTS, exist_ok=True)
    ts = int(time.time())

    output_files = []
    for idx, content in enumerate(batches, start=1):
        out_filename = os.path.join(TEST_OUTPUTS, f"AIS_Digest_{today}_{ts}_part{idx}.txt")
        with open(out_filename, 'w', encoding='utf-8') as f:
            f.write(content)
        output_files.append(out_filename)
        logger.info(f"Digest batch {idx}/{len(batches)} saved locally: {out_filename}")

    logger.info(
        f"Publishing completed in local mode. Insights: {len(normalized_items)}, "
        f"batches: {len(batches)}, byte limit: {byte_limit}."
    )
    stats = {
        "success": True,
        "insights": len(normalized_items),
        "batches": len(batches),
        "byte_limit": byte_limit,
        "output_files": output_files,
        "duplicates_removed": duplicates_removed,
    }
    save_run_stats(BASE_DIR, "publish", stats)
    report_path = write_run_report(today, stats)
    logger.info(f"Run report saved: {report_path}")
    return stats


def write_run_report(today: str, publish_stats: dict) -> str:
    fetch_stats = load_latest_stats(BASE_DIR, "fetch") or {}
    generate_stats = load_latest_stats(BASE_DIR, "generate") or {}

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(TEST_OUTPUTS, f"run_report_{ts}.md")

    lines = [
        f"# AIS Local Run Report ({today})",
        "",
        "## Fetch",
        f"- total_count: {fetch_stats.get('total_count', 'N/A')}",
        f"- arxiv_count: {fetch_stats.get('arxiv_count', 'N/A')}",
        f"- rss_count: {fetch_stats.get('rss_count', 'N/A')}",
        f"- arxiv_max_results: {fetch_stats.get('arxiv_max_results', 'N/A')}",
        f"- rss_max_per_feed: {fetch_stats.get('rss_max_per_feed', 'N/A')}",
        "",
        "## Generate",
        f"- total_candidates: {generate_stats.get('total_candidates', 'N/A')}",
        f"- attempted: {generate_stats.get('attempted', 'N/A')}",
        f"- processed: {generate_stats.get('processed', 'N/A')}",
        f"- skipped_by_score: {generate_stats.get('skipped_by_score', 'N/A')}",
        f"- skipped_non_alpha: {generate_stats.get('skipped_non_alpha', 'N/A')}",
        f"- score_parse_failed: {generate_stats.get('score_parse_failed', 'N/A')}",
        f"- generation_failed: {generate_stats.get('generation_failed', 'N/A')}",
        f"- normalize_failed: {generate_stats.get('normalize_failed', 'N/A')}",
        f"- min_alpha_score: {generate_stats.get('min_alpha_score', 'N/A')}",
        f"- max_items_per_cycle: {generate_stats.get('max_items_per_cycle', 'N/A')}",
        "",
        "## Publish",
        f"- insights: {publish_stats.get('insights', 'N/A')}",
        f"- batches: {publish_stats.get('batches', 'N/A')}",
        f"- byte_limit: {publish_stats.get('byte_limit', 'N/A')}",
        f"- duplicates_removed: {publish_stats.get('duplicates_removed', 'N/A')}",
        "",
        "## Output Files",
    ]
    for path in publish_stats.get("output_files", []):
        lines.append(f"- {path}")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return report_path

if __name__ == "__main__":
    run_ais_publish()
