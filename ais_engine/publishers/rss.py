"""RSS / static-site publisher. Out of scope for v0.1 (scheduled for v0.2)."""

from __future__ import annotations

from models import AlphaSignal, Subscriber
from publishers.base import BasePublisher, DeliveryResult


class RSSPublisher(BasePublisher):
    channel = "rss"

    def publish(
        self,
        signals: list[AlphaSignal],
        subscribers: list[Subscriber],
        *,
        dry_run: bool = False,
    ) -> list[DeliveryResult]:
        raise NotImplementedError("RSSPublisher is scheduled for v0.2.")
