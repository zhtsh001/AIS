import arxiv
import datetime
import feedparser
from ingestors.raw_storage import RawStorageManager
from utils.logger import get_logger

logger = get_logger(__name__)

class ArxivFeed:
    def __init__(self, categories=[
        "cs.AI", "cs.LG", "cs.CL", "cs.CV", # AI
        "q-fin.CP", "q-fin.TR", "quant-ph", # Quant & Quantum
        "cs.ET", "cs.AR",                   # Alternative Computing / Hardware Arch
        "cond-mat.str-el",                  # Advanced Materials / Superconductors
        "math.CO", "math.NT"                # Theoretical Math / Crypto-Math
    ]):
        self.categories = categories
        self.client = arxiv.Client()
        self.storage = RawStorageManager()

    def fetch_latest(self, max_results=5):
        """
        Fetch the most recent papers from specified AI categories.
        """
        query = " OR ".join([f"cat:{cat}" for cat in self.categories])
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        papers = []
        for result in self.client.results(search):
            papers.append({
                "source": "arXiv",
                "title": result.title,
                "summary": result.summary,
                "url": result.entry_id,
                "published": result.published.strftime("%Y-%m-%d")
            })
            
        # 存入原始数据库
        if papers:
            self.storage.save_items("arXiv", papers)
            
        return papers


class RSSFeed:
    def __init__(self):
        self.storage = RawStorageManager()

    def fetch_single_feed(self, url, source_name, max_results=3):
        items = []
        source_items = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_results]:
                summary = entry.get('summary', '') or entry.get('description', '')
                summary = summary[:2000]
                
                item = {
                    "source": source_name,
                    "title": entry.title,
                    "summary": summary,
                    "url": entry.link,
                    "published": entry.get('published', '')
                }
                items.append(item)
                source_items.append(item)
                
            if source_items:
                self.storage.save_items(source_name, source_items)
                
        except Exception as e:
            print(f"Error fetching RSS for {source_name}: {e}")
            
        return items

