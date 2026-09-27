"""BasePublisher contract.

A Publisher is responsible for:
1. Selecting subscribers matching its ``channel``;
2. Rendering signals via a channel-specific Renderer;
3. Transporting the rendered payload(s) to each subscriber;
4. Returning a per-subscriber DeliveryResult so the orchestrator can record
   ``deliveries`` rows for idempotency.

Tier filtering and translation are the orchestrator's job — Publishers
assume the signals/subscribers handed to them are already eligible and the
required language bodies are populated.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from models import AlphaSignal, Subscriber


@dataclass
class DeliveryResult:
    subscriber_id: str
    signal_ids: list[str] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None
    dry_run: bool = False
    payload_preview: Optional[str] = None  # first ~200 chars, for logs / test_outputs


class BasePublisher(ABC):
    #: Must match ``Subscriber.channel`` for routing.
    channel: str = ""

    @abstractmethod
    def publish(
        self,
        signals: list[AlphaSignal],
        subscribers: list[Subscriber],
        *,
        dry_run: bool = False,
    ) -> list[DeliveryResult]:
        """Deliver ``signals`` to every subscriber in ``subscribers``.

        The orchestrator passes ONLY subscribers whose ``channel`` matches
        this publisher's ``channel``. ``signals`` is the full eligible set
        for this publish cycle; the publisher may filter further if
        rendering/transport constraints demand it (rare).

        When ``dry_run`` is True the publisher MUST NOT make network calls;
        it should still populate ``payload_preview`` so the orchestrator can
        archive a sample to ``test_outputs/``.
        """
        raise NotImplementedError
