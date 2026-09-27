"""SQLite-backed subscriber + delivery store.

Two tables:
- ``subscribers`` — one row per addressable destination (channel + address).
- ``deliveries`` — composite key (signal_id, subscriber_id) used for
  idempotency: the orchestrator records a row after each send and skips
  already-recorded pairs on subsequent runs.

API surface used by the orchestrator and CLI scripts:
    init_db(db_path)
    add_subscriber(db_path, subscriber) -> Subscriber
    remove_subscriber(db_path, id) -> bool
    list_active(db_path, channel=None, tier=None) -> list[Subscriber]
    list_all(db_path) -> list[Subscriber]
    mark_delivered(db_path, signal_id, subscriber_id, status)
    already_delivered(db_path, signal_id, subscriber_id) -> bool

Everything goes through these helpers; raw SQL stays inside this module.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

from models import Subscriber, utcnow_iso


# Base CREATE TABLE statements. Run FIRST; if the table already exists
# from a previous (pre-Phase-A) install, this is a no-op and ``_migrate``
# adds the new columns below.
_BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscribers (
  id TEXT PRIMARY KEY,
  channel TEXT NOT NULL DEFAULT 'email',
  address TEXT NOT NULL,
  langs TEXT NOT NULL DEFAULT 'zh',
  tier TEXT NOT NULL DEFAULT 'free',
  active INTEGER NOT NULL DEFAULT 1,
  confirmed INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  paid_until TEXT,
  delivery_hour INTEGER NOT NULL DEFAULT 8,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  cadence TEXT NOT NULL DEFAULT 'daily',
  confirmation_token TEXT,
  unsubscribe_token TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS deliveries (
  signal_id TEXT NOT NULL,
  subscriber_id TEXT NOT NULL,
  sent_at TEXT NOT NULL,
  status TEXT NOT NULL,
  PRIMARY KEY (signal_id, subscriber_id)
);
"""

# Indices created AFTER migrations — they reference columns that the
# migration step may have just added on legacy databases.
_INDICES = """
CREATE INDEX IF NOT EXISTS idx_subscribers_channel_active
  ON subscribers (channel, active);

CREATE INDEX IF NOT EXISTS idx_subscribers_tick
  ON subscribers (active, confirmed, delivery_hour);

CREATE UNIQUE INDEX IF NOT EXISTS idx_subscribers_unsubscribe_token
  ON subscribers (unsubscribe_token)
  WHERE unsubscribe_token != '';
"""

# Compat alias for callers that imported SCHEMA before the split.
SCHEMA = _BASE_SCHEMA + _INDICES


# Per-column ALTER statements applied idempotently after CREATE.
# Each entry: (column_name, ALTER fragment). Run only when the column is
# missing — SQLite has no IF NOT EXISTS for ADD COLUMN.
_ADDITIVE_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("langs",               "ALTER TABLE subscribers ADD COLUMN langs TEXT NOT NULL DEFAULT 'zh'"),
    ("confirmed",           "ALTER TABLE subscribers ADD COLUMN confirmed INTEGER NOT NULL DEFAULT 0"),
    ("delivery_hour",       "ALTER TABLE subscribers ADD COLUMN delivery_hour INTEGER NOT NULL DEFAULT 8"),
    ("timezone",            "ALTER TABLE subscribers ADD COLUMN timezone TEXT NOT NULL DEFAULT 'UTC'"),
    ("cadence",             "ALTER TABLE subscribers ADD COLUMN cadence TEXT NOT NULL DEFAULT 'daily'"),
    ("confirmation_token",  "ALTER TABLE subscribers ADD COLUMN confirmation_token TEXT"),
    ("unsubscribe_token",   "ALTER TABLE subscribers ADD COLUMN unsubscribe_token TEXT NOT NULL DEFAULT ''"),
)


def _migrate(conn: sqlite3.Connection) -> None:
    """Bring an existing v0.1 database up to the current schema in-place.

    Idempotent: each ADD COLUMN check uses PRAGMA table_info; nothing runs
    if the column is already there. Also forward-fills ``langs`` from the
    legacy ``lang`` column when present, so old subscriber rows keep working.
    """
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(subscribers)").fetchall()}
    has_legacy_lang = "lang" in existing_cols

    for col, sql in _ADDITIVE_MIGRATIONS:
        if col not in existing_cols:
            conn.execute(sql)
            existing_cols.add(col)

    if has_legacy_lang:
        # Copy ``lang`` into the new ``langs`` column for rows that still
        # have the default. After this, the legacy ``lang`` column stays in
        # place (SQLite makes DROP COLUMN awkward) but is no longer read.
        conn.execute("UPDATE subscribers SET langs = lang WHERE langs = 'zh' AND lang IS NOT NULL AND lang != ''")
    conn.commit()


def init_db(db_path: str) -> None:
    parent = os.path.dirname(db_path) or "."
    os.makedirs(parent, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        # 1) Base tables (no-op on existing legacy DBs).
        conn.executescript(_BASE_SCHEMA)
        # 2) Add any missing columns before any index touches them.
        _migrate(conn)
        # 3) Indices — safe now that all referenced columns exist.
        conn.executescript(_INDICES)
        conn.commit()


@contextmanager
def connect(db_path: str) -> Iterator[sqlite3.Connection]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Subscribers CRUD
# --------------------------------------------------------------------------- #

def _row_to_sub(row: sqlite3.Row) -> Subscriber:
    keys = row.keys()
    langs_blob = row["langs"] if "langs" in keys else (row["lang"] if "lang" in keys else "zh")
    langs = [l.strip() for l in (langs_blob or "zh").split(",") if l.strip()] or ["zh"]
    return Subscriber(
        id=row["id"],
        channel=row["channel"],
        address=row["address"],
        langs=langs,
        tier=row["tier"],
        active=bool(row["active"]),
        confirmed=bool(row["confirmed"]) if "confirmed" in keys else False,
        paid_until=row["paid_until"],
        created_at=row["created_at"],
        delivery_hour=row["delivery_hour"] if "delivery_hour" in keys else 8,
        timezone=row["timezone"] if "timezone" in keys else "UTC",
        cadence=row["cadence"] if "cadence" in keys else "daily",
        confirmation_token=row["confirmation_token"] if "confirmation_token" in keys else None,
        unsubscribe_token=row["unsubscribe_token"] if "unsubscribe_token" in keys else "",
    )


def add_subscriber(db_path: str, sub: Subscriber) -> Subscriber:
    if not sub.created_at:
        sub.created_at = utcnow_iso()
    langs_blob = ",".join(sub.langs) if sub.langs else "zh"
    with connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO subscribers
               (id, channel, address, langs, tier, active, confirmed, created_at,
                paid_until, delivery_hour, timezone, cadence,
                confirmation_token, unsubscribe_token)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sub.id,
                sub.channel,
                sub.address,
                langs_blob,
                sub.tier,
                1 if sub.active else 0,
                1 if sub.confirmed else 0,
                sub.created_at,
                sub.paid_until,
                sub.delivery_hour,
                sub.timezone,
                sub.cadence,
                sub.confirmation_token,
                sub.unsubscribe_token,
            ),
        )
        conn.commit()
    return sub


def find_by_email(db_path: str, email: str) -> Optional[Subscriber]:
    """Look up by ``address`` column, case-insensitive — used by the
    subscription server to detect duplicate signups before issuing a new
    confirmation token."""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM subscribers WHERE channel = 'email' AND lower(address) = lower(?)",
            (email,),
        ).fetchone()
        return _row_to_sub(row) if row else None


def find_by_confirmation_token(db_path: str, token: str) -> Optional[Subscriber]:
    if not token:
        return None
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM subscribers WHERE confirmation_token = ?",
            (token,),
        ).fetchone()
        return _row_to_sub(row) if row else None


def find_by_unsubscribe_token(db_path: str, token: str) -> Optional[Subscriber]:
    if not token:
        return None
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM subscribers WHERE unsubscribe_token = ?",
            (token,),
        ).fetchone()
        return _row_to_sub(row) if row else None


def confirm(db_path: str, token: str) -> Optional[Subscriber]:
    """Confirm-on-use: flip confirmed=True/active=True and null the one-time
    token. Returns the updated subscriber, or None if the token didn't match.

    Two-step rather than UPDATE … RETURNING because we still target SQLite
    versions older than 3.35. Look up first to grab the id, then update.
    """
    if not token:
        return None
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM subscribers WHERE confirmation_token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        sub_id = row["id"]
        conn.execute(
            """UPDATE subscribers
               SET confirmed = 1, active = 1, confirmation_token = NULL
               WHERE id = ?""",
            (sub_id,),
        )
        conn.commit()
    return get_subscriber(db_path, sub_id)


def unsubscribe(db_path: str, token: str) -> Optional[Subscriber]:
    """Deactivate by ``unsubscribe_token``. Returns the updated row or None
    if the token didn't match."""
    if not token:
        return None
    with connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE subscribers SET active = 0 WHERE unsubscribe_token = ?",
            (token,),
        )
        if cur.rowcount == 0:
            return None
        conn.commit()
    return find_by_unsubscribe_token(db_path, token)


def remove_subscriber(db_path: str, subscriber_id: str) -> bool:
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM subscribers WHERE id = ?", (subscriber_id,))
        conn.commit()
        return cur.rowcount > 0


def get_subscriber(db_path: str, subscriber_id: str) -> Optional[Subscriber]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM subscribers WHERE id = ?", (subscriber_id,)
        ).fetchone()
        return _row_to_sub(row) if row else None


def list_active(
    db_path: str,
    channel: Optional[str] = None,
    tier: Optional[str] = None,
    only_confirmed: bool = False,
) -> list[Subscriber]:
    """List subscribers with ``active = 1``.

    Set ``only_confirmed=True`` for the tick orchestrator's dispatch loop —
    pending (unconfirmed) signups should never receive content.
    """
    sql = "SELECT * FROM subscribers WHERE active = 1"
    params: list = []
    if only_confirmed:
        sql += " AND confirmed = 1"
    if channel is not None:
        sql += " AND channel = ?"
        params.append(channel)
    if tier is not None:
        sql += " AND tier = ?"
        params.append(tier)
    sql += " ORDER BY created_at ASC"
    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_sub(r) for r in rows]


def list_all(db_path: str) -> list[Subscriber]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM subscribers ORDER BY created_at ASC").fetchall()
        return [_row_to_sub(r) for r in rows]


# --------------------------------------------------------------------------- #
# Deliveries (idempotency)
# --------------------------------------------------------------------------- #

def already_delivered(db_path: str, signal_id: str, subscriber_id: str) -> bool:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM deliveries WHERE signal_id = ? AND subscriber_id = ?",
            (signal_id, subscriber_id),
        ).fetchone()
        return row is not None


def mark_delivered(
    db_path: str,
    signal_id: str,
    subscriber_id: str,
    status: str,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO deliveries
               (signal_id, subscriber_id, sent_at, status)
               VALUES (?, ?, ?, ?)""",
            (signal_id, subscriber_id, utcnow_iso(), status),
        )
        conn.commit()


def filter_undelivered(
    db_path: str,
    signal_ids: list[str],
    subscriber_id: str,
) -> list[str]:
    """Return the subset of ``signal_ids`` that have NOT been delivered to
    ``subscriber_id`` yet — used by the orchestrator to avoid re-sending."""
    if not signal_ids:
        return []
    placeholders = ",".join("?" * len(signal_ids))
    with connect(db_path) as conn:
        rows = conn.execute(
            f"""SELECT signal_id FROM deliveries
                WHERE subscriber_id = ?
                  AND signal_id IN ({placeholders})""",
            [subscriber_id, *signal_ids],
        ).fetchall()
        already = {r["signal_id"] for r in rows}
        return [sid for sid in signal_ids if sid not in already]
