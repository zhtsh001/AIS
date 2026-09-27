#!/usr/bin/env python3
import os
import time
from datetime import datetime, timezone, timedelta

from ingestors.rss_arxiv import ArxivFeed, RSSFeed
from ingestors.github import GithubTrendingFeed
from utils.config import load_config, load_sources
from utils.run_stats import save_run_stats

def is_source_due(frequency_hint: str) -> bool:
    """
    判断该信源当前是否需要抓取。
    - hourly/realtime: 总是抓取
    - daily/weekly: 简化逻辑，在每天北京时间早上 4点~6点 之间触发时才抓取
    """
    if frequency_hint in ["hourly", "realtime"]:
        return True
    
    # 获取北京时间 (UTC+8)
    bj_time = datetime.now(timezone(timedelta(hours=8)))
    if 4 <= bj_time.hour <= 6:
        return True
    return False

def hourly_raw_fetch():
    print(f"[{time.ctime()}] 启动 AIS 原始信息源抓取 (Sources.yaml 驱动)...")

    base_dir = os.path.dirname(__file__)
    cfg = load_config(base_dir)
    sources = load_sources(base_dir)
    
    # 统计项
    arxiv_count = 0
    rss_count = 0
    github_count = 0
    errors = []

    # 初始化抓取器
    feed_arxiv = ArxivFeed()
    feed_rss = RSSFeed()
    feed_github = GithubTrendingFeed()

    for src in sources:
        if not src.get("active"):
            continue
            
        freq = src.get("frequency_hint", "daily")
        if not is_source_due(freq):
            print(f"Skipping {src['name']} (Not due for {freq} frequency).")
            continue
            
        src_type = src.get("type")
        url_or_tag = src.get("url")
        print(f"Fetching {src['name']} ({src_type})...")
        
        try:
            if src_type == "arxiv":
                feed_arxiv.categories = url_or_tag.split("+OR+")
                papers = feed_arxiv.fetch_latest(max_results=10)
                arxiv_count += len(papers)
            elif src_type == "rss":
                # 将原来的 RSSFeed 改为接收单条 URL 处理
                items = feed_rss.fetch_single_feed(url_or_tag, src["name"], max_results=3)
                rss_count += len(items)
            elif src_type == "github_trending":
                items = feed_github.fetch_latest(languages=url_or_tag, max_results=5)
                github_count += len(items)
            else:
                print(f"Warning: Unsupported source type '{src_type}' for {src['name']}")
        except Exception as e:
            err_msg = f"{src['id']} failed: {e}"
            errors.append(err_msg)
            print(err_msg)

    print("抓取完毕！数据已通过 RawStorageManager 自动分类保存并清理冗余。")

    stats = {
        "success": len(errors) == 0,
        "arxiv_count": arxiv_count,
        "rss_count": rss_count,
        "github_count": github_count,
        "total_count": arxiv_count + rss_count + github_count,
        "errors": errors,
    }
    save_run_stats(base_dir, "fetch", stats)
    return stats

if __name__ == "__main__":
    hourly_raw_fetch()
