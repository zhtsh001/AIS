import datetime
import requests
from ingestors.raw_storage import RawStorageManager
from utils.logger import get_logger

logger = get_logger(__name__)

class GithubTrendingFeed:
    def __init__(self):
        self.base_url = "https://api.github.com/search/repositories"
        self.storage = RawStorageManager()

    def fetch_latest(self, languages: str, max_results=5):
        """
        通过 GitHub Search API 模拟获取指定语言近期的热门项目。
        由于官方并没有直接的 Trending API，这里采用：
        查找最近 7 天内创建且按 stars 倒序排列的项目，作为高潜力爆发黑马的代餐。
        
        :param languages: 逗号分隔的语言列表，如 "python,jupyter-notebook"
        """
        langs = [l.strip() for l in languages.split(",") if l.strip()]
        seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        items = []
        for lang in langs:
            query = f"language:{lang} created:>{seven_days_ago}"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results
            }
            # 为了防止被 GitHub API 速率限制，设置合适的 Headers
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "OpenClaw-AIS-Agent/1.0"
            }
            
            try:
                resp = requests.get(self.base_url, params=params, headers=headers, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                
                for repo in data.get("items", [])[:max_results]:
                    # 组装成统一格式的字典
                    items.append({
                        "source": f"GitHub Trending ({lang})",
                        "title": repo.get("full_name"),
                        "url": repo.get("html_url"),
                        "summary": repo.get("description") or "No description provided.",
                        "date": repo.get("created_at"),
                        "stars": repo.get("stargazers_count", 0),
                        "language": lang
                    })
            except Exception as e:
                logger.error(f"Failed to fetch GitHub trends for language {lang}: {e}")
                
        # 存入本地 raw_storage
        saved = []
        for item in items:
            if self.storage.save_items(item["source"], [item]):
                saved.append(item)
                
        return saved
