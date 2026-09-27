import os
from typing import Any

import yaml


def load_sources(base_dir: str) -> list[dict]:
    """Reconstructed loader for the recovered source registry."""
    with open(os.path.join(base_dir, "sources.yaml"), encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    sources = data.get("sources", [])
    if not isinstance(sources, list) or any(not isinstance(s, dict) for s in sources):
        raise ValueError("sources.yaml must contain a list of source objects")
    return sources


DEFAULT_CONFIG = {
    "feeds": {
        "rss_max_per_feed": 1,
        "arxiv_max_results": 5,
    },
    "scoring": {
        "min_alpha_score": 0.0,
        "max_items_per_cycle": 10,
    },
    "generation": {
        "worker_count": 2,
        "score_timeout_sec": 12,
        "generate_timeout_sec": 35,
        "score_max_retries": 1,
        "generate_max_retries": 2,
        "retry_backoff_sec": 2,
    },
    "delivery": {
        "batch_byte_limit": 1800,
        "separator": "\n━━━━━━━━━━━━━━\n",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(base_dir: str) -> dict[str, Any]:
    config_path = os.path.join(base_dir, "config.yaml")
    if not os.path.exists(config_path):
        return dict(DEFAULT_CONFIG)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            return dict(DEFAULT_CONFIG)
        return _deep_merge(DEFAULT_CONFIG, loaded)
    except Exception:
        return dict(DEFAULT_CONFIG)
