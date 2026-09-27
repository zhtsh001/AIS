"""Channel-agnostic data models shared by generators, publishers, and subscriber store.

These dataclasses are the canonical wire format between pipeline stages:
- ``AlphaSignal`` is produced by ``generate.py`` (one per scored source item),
  serialized to ``data/generated/{date}/{id}.json``, and consumed by the
  publisher orchestrator.
- ``Subscriber`` represents an addressable delivery target (one row in the
  SQLite subscribers store), regardless of channel.

The structures are intentionally pure data — no I/O, no behavior — so they
can be reused by any future Publisher / Renderer without coupling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional


Language = Literal["zh", "en"]
Channel = Literal["telegram", "email", "rss", "feishu", "wechat"]
Tier = Literal["free", "paid"]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class AlphaSignal:
    """One scored, generated signal ready for delivery.

    ``bodies`` keys are language codes (``"zh"`` / ``"en"``). The signal is
    initially produced with a single body in ``source_lang``; translator fills
    in additional language entries lazily at publish time.

    ``paid_only_fields`` carries fields that should be hidden from free-tier
    subscribers (e.g. ``source_url`` once the paid product launches). v0.1
    keeps this open to everyone, but renderers consult tier so the gate is
    already wired.
    """

    id: str                                                # url hash, stable across runs
    source_url: str
    source_lang: Language
    source: str = ""                                       # human-readable source label (e.g., "arXiv cs.LG")
    title: str = ""
    score: float = 0.0
    tier: Tier = "free"                                    # minimum tier required to receive
    bodies: dict[str, str] = field(default_factory=dict)   # {lang: rendered five-module text}
    paid_only_fields: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AlphaSignal":
        # Tolerate unknown / missing keys so old JSON blobs still load.
        known = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in data.items() if k in known}
        return cls(**clean)

    def body_for(self, lang: Language) -> Optional[str]:
        """Return body in requested language, falling back to source_lang."""
        return self.bodies.get(lang) or self.bodies.get(self.source_lang)


Cadence = Literal["daily", "weekly"]


@dataclass
class Subscriber:
    """One addressable delivery target.

    ``id`` is a stable opaque identifier (e.g. ``em:abc123``) used as the
    primary key in the SQLite store and the dedupe key in the ``deliveries``
    table.

    Scheduling fields (``delivery_hour`` + ``timezone`` + ``cadence``) drive
    the tick orchestrator: every hour at ``:05`` the orchestrator walks
    confirmed subscribers, asks ``now_utc.astimezone(tz).hour ==
    delivery_hour`` and ``_cadence_due(now_local, cadence)`` — only matches
    receive content this cycle.

    Token fields enable the public subscription flow:
    - ``confirmation_token`` is single-use, generated at signup and cleared
      on first GET /confirm; ``confirmed`` flips True at that point.
    - ``unsubscribe_token`` is permanent — embedded in every outgoing email
      footer so the user can one-click opt out.
    """

    id: str
    channel: Channel = "email"
    address: str = ""                                      # email addr (v0.1); tg chat_id reserved
    langs: list[str] = field(default_factory=lambda: ["zh"])  # multi-select: ["zh"] | ["en"] | ["zh","en"]
    tier: Tier = "free"
    active: bool = True
    confirmed: bool = False                                # set True after double-opt-in
    paid_until: Optional[str] = None                       # ISO timestamp, None for free
    created_at: str = field(default_factory=utcnow_iso)
    # Scheduling
    delivery_hour: int = 8                                 # 0-23, in subscriber's local time
    timezone: str = "UTC"                                  # IANA tz, e.g. "Asia/Shanghai"
    cadence: Cadence = "daily"                             # default daily; flipped to weekly post-paid launch
    # Tokens
    confirmation_token: Optional[str] = None
    unsubscribe_token: str = ""

    @property
    def lang(self) -> Language:
        """Back-compat shim: callers that still ask for a single ``lang``
        get the first selected language (or ``"zh"`` as a defensive default)."""
        return self.langs[0] if self.langs else "zh"  # type: ignore[return-value]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Subscriber":
        known = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in data.items() if k in known}
        # Tolerate legacy single-``lang`` payloads.
        if "lang" in data and "langs" not in data:
            clean["langs"] = [data["lang"]]
        return cls(**clean)
