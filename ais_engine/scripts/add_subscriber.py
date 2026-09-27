#!/usr/bin/env python3
"""Add or update one subscriber in the SQLite store.

Usage examples:

    # Add yourself as an email subscriber, BJ time 8am, both langs:
    python scripts/add_subscriber.py \\
        --id em:tristan --channel email --address me@example.com \\
        --langs zh,en --tz Asia/Shanghai --hour 8 --confirmed

    # Deactivate someone:
    python scripts/add_subscriber.py --id em:tristan --deactivate

The script writes to ``data/subscribers.db`` (relative to ``ais_engine/``).
``--confirmed`` skips double-opt-in for trusted manual entries.
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from models import Subscriber  # noqa: E402
from subscribers import store  # noqa: E402
from subscribers.tokens import new_token  # noqa: E402
from utils.config import load_config  # noqa: E402


def _db_path() -> str:
    base = os.path.dirname(HERE)
    cfg = load_config(base)
    rel = (cfg.get("subscribers") or {}).get("db_path", "data/subscribers.db")
    return os.path.join(base, rel)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage AIS subscribers (SQLite).")
    parser.add_argument("--id", required=True, help="Stable subscriber id (e.g. 'em:tristan').")
    parser.add_argument("--channel", choices=["telegram", "email", "rss"], default="email")
    parser.add_argument("--address", help="Channel-specific address (email, chat_id, feed_id).")
    parser.add_argument("--langs", default="zh", help="Comma-separated langs, e.g. 'zh' or 'zh,en'.")
    parser.add_argument("--tier", choices=["free", "paid"], default="free")
    parser.add_argument("--paid-until", default=None, help="ISO timestamp for paid expiration.")
    parser.add_argument("--hour", type=int, default=8, help="Delivery hour (0-23) in local TZ.")
    parser.add_argument("--tz", default="UTC", help="IANA timezone, e.g. 'Asia/Shanghai'.")
    parser.add_argument("--cadence", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--confirmed", action="store_true",
                        help="Skip double-opt-in (only for manual / trusted entries).")
    parser.add_argument("--deactivate", action="store_true")
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args(argv)

    db = _db_path()
    store.init_db(db)

    if args.remove:
        ok = store.remove_subscriber(db, args.id)
        print(f"{'Removed' if ok else 'Not found'}: {args.id}")
        return 0 if ok else 1

    if args.deactivate:
        existing = store.get_subscriber(db, args.id)
        if not existing:
            print(f"Not found: {args.id}", file=sys.stderr)
            return 1
        existing.active = False
        store.add_subscriber(db, existing)
        print(f"Deactivated: {args.id}")
        return 0

    if not args.address:
        parser.error("--address is required when adding/updating a subscriber.")

    langs = [l.strip() for l in args.langs.split(",") if l.strip()]
    if not langs:
        parser.error("--langs must contain at least one of zh,en.")
    for l in langs:
        if l not in ("zh", "en"):
            parser.error(f"unsupported lang: {l}")

    if not (0 <= args.hour <= 23):
        parser.error("--hour must be in 0..23")

    existing = store.get_subscriber(db, args.id)
    unsubscribe_token = existing.unsubscribe_token if existing and existing.unsubscribe_token else new_token()

    sub = Subscriber(
        id=args.id,
        channel=args.channel,
        address=args.address,
        langs=langs,
        tier=args.tier,
        active=True,
        confirmed=args.confirmed,
        paid_until=args.paid_until,
        delivery_hour=args.hour,
        timezone=args.tz,
        cadence=args.cadence,
        confirmation_token=None if args.confirmed else (existing.confirmation_token if existing else new_token()),
        unsubscribe_token=unsubscribe_token,
    )
    store.add_subscriber(db, sub)
    print(f"Saved: {sub.to_dict()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
