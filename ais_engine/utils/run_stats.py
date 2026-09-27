import json
import os
import time
from datetime import datetime
from typing import Any


def _stats_root(base_dir: str) -> str:
    return os.path.join(base_dir, "data", "run_stats")


def save_run_stats(base_dir: str, module: str, payload: dict[str, Any]) -> str:
    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    ts = int(time.time())

    root = _stats_root(base_dir)
    day_dir = os.path.join(root, day)
    os.makedirs(day_dir, exist_ok=True)

    body = {
        "module": module,
        "timestamp": now.isoformat(),
        **payload,
    }

    out_file = os.path.join(day_dir, f"{module}_{ts}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)

    latest_file = os.path.join(root, f"{module}_latest.json")
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)

    return out_file


def load_latest_stats(base_dir: str, module: str) -> dict[str, Any] | None:
    latest_file = os.path.join(_stats_root(base_dir), f"{module}_latest.json")
    if not os.path.exists(latest_file):
        return None
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
