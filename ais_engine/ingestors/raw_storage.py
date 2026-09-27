import os
import json
from datetime import datetime
import shutil

# Default to ais_engine/data/raw
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'raw')
DEFAULT_INDEX_FILE = os.path.join(os.path.dirname(DEFAULT_DATA_DIR), 'index', 'url_index.json')

class RawStorageManager:
    """
    负责将抓取到的原始信息按天、按来源分类存储，并实施存储上限（时间和空间）淘汰机制。
    """
    def __init__(self, base_dir=DEFAULT_DATA_DIR, max_days=30, max_mb=100, index_file=DEFAULT_INDEX_FILE):
        self.base_dir = base_dir
        self.max_days = max_days
        self.max_mb = max_mb
        self.index_file = index_file
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)

    def _clean_source_name(self, name):
        """将源名称转换为安全的文件名"""
        return "".join([c if c.isalnum() else "_" for c in name])

    def save_items(self, source_name, items):
        """
        保存原始内容。
        目录结构: data/raw/YYYY-MM-DD/source_name.json
        """
        if not items:
            return 0
            
        today = datetime.now().strftime('%Y-%m-%d')
        safe_source = self._clean_source_name(source_name)
        day_dir = os.path.join(self.base_dir, today)
        os.makedirs(day_dir, exist_ok=True)
        
        file_path = os.path.join(day_dir, f"{safe_source}.json")
        
        # 加载当天已有的数据（同天同 URL 合并计数，跨天不去重）
        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    pass

        daily_by_url = {item.get('url'): item for item in existing_data if item.get('url')}
        index_data = self._load_index()
        touched = False
        new_unique_today = 0
        today = datetime.now().strftime('%Y-%m-%d')

        for item in items:
            url = item.get('url')
            if not url:
                continue

            now_iso = datetime.now().isoformat()
            daily_existing = daily_by_url.get(url)
            if daily_existing:
                daily_existing['seen_count_day'] = int(daily_existing.get('seen_count_day', 1)) + 1
                daily_existing['last_fetched_at'] = now_iso
            else:
                row = dict(item)
                row['first_fetched_at'] = now_iso
                row['last_fetched_at'] = now_iso
                row['seen_count_day'] = 1
                existing_data.append(row)
                daily_by_url[url] = row
                new_unique_today += 1

            self._update_global_index(
                index_data=index_data,
                url=url,
                source_name=source_name,
                title=item.get('title', ''),
                published=item.get('published', ''),
                day=today,
                seen_at=now_iso
            )
            touched = True

        if touched:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            self._save_index(index_data)
            
        # 每次保存后，触发强制清理策略
        self.enforce_limits()
        
        return new_unique_today

    def _load_index(self):
        if not os.path.exists(self.index_file):
            return {"urls": {}, "updated_at": None}
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("urls"), dict):
                return data
        except Exception:
            pass
        return {"urls": {}, "updated_at": None}

    def _save_index(self, index_data):
        index_data["updated_at"] = datetime.now().isoformat()
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

    def _update_global_index(self, index_data, url, source_name, title, published, day, seen_at):
        urls = index_data.setdefault("urls", {})
        record = urls.get(url)
        if not record:
            urls[url] = {
                "first_seen_at": seen_at,
                "last_seen_at": seen_at,
                "seen_count": 1,
                "sources": [source_name],
                "days_seen": [day],
                "latest_title": title,
                "latest_published": published,
            }
            return

        record["last_seen_at"] = seen_at
        record["seen_count"] = int(record.get("seen_count", 0)) + 1
        record["latest_title"] = title or record.get("latest_title", "")
        record["latest_published"] = published or record.get("latest_published", "")

        sources = set(record.get("sources", []))
        sources.add(source_name)
        record["sources"] = sorted(sources)

        days_seen = set(record.get("days_seen", []))
        days_seen.add(day)
        record["days_seen"] = sorted(days_seen)

    def enforce_limits(self):
        """
        执行双重淘汰机制：
        1. 删掉超过 max_days 天的文件夹
        2. 如果总大小超过 max_mb，从最老的文件夹开始删
        """
        # 1. 淘汰超期文件
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            if os.path.isdir(item_path):
                try:
                    folder_date = datetime.strptime(item, '%Y-%m-%d')
                    if (datetime.now() - folder_date).days > self.max_days:
                        shutil.rmtree(item_path)
                        print(f"[Storage] Deleted expired raw data folder: {item}")
                except ValueError:
                    pass

        # 2. 淘汰超容文件 (按大小限制)
        def get_dir_size(path):
            total = 0
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
            return total
        
        max_bytes = self.max_mb * 1024 * 1024
        while get_dir_size(self.base_dir) > max_bytes:
            dirs = [os.path.join(self.base_dir, d) for d in os.listdir(self.base_dir) 
                    if os.path.isdir(os.path.join(self.base_dir, d))]
            if not dirs:
                break
            # 找到修改时间最早的文件夹（最老的数据）
            oldest_dir = min(dirs, key=os.path.getmtime)
            shutil.rmtree(oldest_dir)
            print(f"[Storage] Storage exceeded {self.max_mb}MB. Deleted oldest folder: {os.path.basename(oldest_dir)}")

if __name__ == "__main__":
    # Test script
    manager = RawStorageManager()
    manager.save_items("test_source", [{"title": "Test 1", "url": "http://test.com/1"}])
    print(f"Test saved to: {manager.base_dir}")
