import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo


STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "schedule_state")


def bj_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def is_bj_time(hour: int, minute: int, weekday: int | None = None) -> bool:
    now = bj_now()
    if weekday is not None and now.weekday() != weekday:
        return False
    return now.hour == hour and now.minute == minute


def is_bj_time_in_window(hour: int, minute: int, window_minutes: int, weekday: int | None = None) -> bool:
    now = bj_now()
    if weekday is not None and now.weekday() != weekday:
        return False
    now_minutes = now.hour * 60 + now.minute
    target_minutes = hour * 60 + minute
    return target_minutes <= now_minutes < target_minutes + window_minutes


def already_ran_today(task_name: str) -> bool:
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{task_name}.json")
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("date") == bj_now().strftime("%Y-%m-%d")
    except Exception:
        return False


def mark_ran_today(task_name: str) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    path = os.path.join(STATE_DIR, f"{task_name}.json")
    body = {
        "date": bj_now().strftime("%Y-%m-%d"),
        "ts_bj": bj_now().isoformat(),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)
