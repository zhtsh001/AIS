"""Feishu / Lark webhook publisher. Stubbed: not in v0.1 because Feishu
messages cannot be rendered natively inside WeChat (different ecosystems).

Keep the stub so the BasePublisher contract is exercised by ``mypy`` /
unit tests and so adding Feishu later is a fill-in-the-method operation.
"""

from __future__ import annotations

from models import AlphaSignal, Subscriber
from publishers.base import BasePublisher, DeliveryResult


class FeishuPublisher(BasePublisher):
    channel = "feishu"

    def publish(
        self,
        signals: list[AlphaSignal],
        subscribers: list[Subscriber],
        *,
        dry_run: bool = False,
    ) -> list[DeliveryResult]:
        raise NotImplementedError("FeishuPublisher is not in v0.1 scope.")
