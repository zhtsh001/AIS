"""Plaintext renderer — channel-neutral fallback used by the orchestrator's
dry-run archive (``test_outputs/``) and by any future plain-text channel.

Behavior mirrors the legacy ``publish.split_batches`` so v0.1 dry-runs
produce diffs that look familiar:
- Items joined by a thin horizontal separator
- Optional byte budget per output payload (UTF-8 measured)
- Single-item overflow is kept whole (rather than truncated)
"""

from __future__ import annotations

from typing import Optional

from models import AlphaSignal, Subscriber
from publishers.renderers.base import BaseRenderer


DEFAULT_SEPARATOR = "\n━━━━━━━━━━━━━━\n"


class PlaintextRenderer(BaseRenderer):
    def __init__(
        self,
        max_bytes: Optional[int] = None,
        separator: str = DEFAULT_SEPARATOR,
    ) -> None:
        self.max_bytes = max_bytes
        self.separator = separator

    def _pick_body(self, signal: AlphaSignal, lang: str) -> str:
        body = signal.body_for(lang) or ""  # type: ignore[arg-type]
        return body.strip()

    def render(self, signals: list[AlphaSignal], subscriber: Subscriber) -> list[str]:
        items = [b for s in signals if (b := self._pick_body(s, subscriber.lang))]
        if not items:
            return []

        if self.max_bytes is None:
            return [self.separator.join(items)]

        batches: list[str] = []
        current = ""
        for item in items:
            candidate = item if not current else f"{current}{self.separator}{item}"
            if len(candidate.encode("utf-8")) <= self.max_bytes:
                current = candidate
                continue
            if current:
                batches.append(current)
                current = item
            else:
                # Single item exceeds budget on its own — emit whole.
                batches.append(item)
                current = ""
        if current:
            batches.append(current)
        return batches
