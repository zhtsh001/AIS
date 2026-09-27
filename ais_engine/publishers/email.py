"""Email publisher.

Two supported transports:
- ``resend``: HTTP API. Requires ``RESEND_API_KEY`` and a verified ``from``.
- ``smtp``:   stdlib ``smtplib``. Requires ``SMTP_HOST`` / ``SMTP_PORT`` /
              ``SMTP_USER`` / ``SMTP_PASSWORD`` env vars.

Subject is generated from the first signal's body language so the user sees
familiar copy. One email per subscriber per cycle aggregating all eligible
signals (avoids inbox spam from per-signal sends).
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

import requests

from models import AlphaSignal, Subscriber
from publishers.base import BasePublisher, DeliveryResult
from publishers.renderers.html import HTMLRenderer, render_subject
from utils.logger import get_logger

logger = get_logger(__name__)


class EmailPublisher(BasePublisher):
    channel = "email"

    def __init__(
        self,
        sender: str,
        transport: str = "resend",
        api_key: str | None = None,
        renderer: HTMLRenderer | None = None,
        request_timeout: int = 15,
        public_origin: str | None = None,
        mode: str = "free",
        cadence_label: str = "daily",
    ) -> None:
        if not sender:
            raise ValueError("EmailPublisher requires a sender (env via config.publishers.email.from_env).")
        self.sender = sender
        self.transport = transport
        self.api_key = api_key
        self.renderer = renderer or HTMLRenderer(
            mode=mode,
            cadence_label=cadence_label,
            public_origin=public_origin,
        )
        self.request_timeout = request_timeout

    # -------------------------------------------------------------------- #
    # BasePublisher contract
    # -------------------------------------------------------------------- #

    def publish(
        self,
        signals: list[AlphaSignal],
        subscribers: list[Subscriber],
        *,
        dry_run: bool = False,
    ) -> list[DeliveryResult]:
        results: list[DeliveryResult] = []
        signal_ids = [s.id for s in signals]

        for sub in subscribers:
            if sub.channel != self.channel:
                continue

            html_bodies = self.renderer.render(signals, sub)
            if not html_bodies:
                results.append(
                    DeliveryResult(
                        subscriber_id=sub.id, signal_ids=signal_ids,
                        success=True, dry_run=dry_run,
                    )
                )
                continue
            body = html_bodies[0]
            subject = render_subject(sub.lang, len(signals))

            if dry_run:
                results.append(
                    DeliveryResult(
                        subscriber_id=sub.id, signal_ids=signal_ids,
                        success=True, dry_run=True,
                        payload_preview=body[:200],
                    )
                )
                continue

            ok, err = self._send(sub.address, subject, body)
            results.append(
                DeliveryResult(
                    subscriber_id=sub.id, signal_ids=signal_ids,
                    success=ok, error=err,
                    payload_preview=body[:200],
                )
            )
        return results

    # -------------------------------------------------------------------- #
    # Transports
    # -------------------------------------------------------------------- #

    def _send(self, to_addr: str, subject: str, body_html: str) -> tuple[bool, str | None]:
        if self.transport == "resend":
            return self._send_resend(to_addr, subject, body_html)
        if self.transport == "smtp":
            return self._send_smtp(to_addr, subject, body_html)
        return False, f"unknown email transport: {self.transport}"

    def _send_resend(self, to_addr: str, subject: str, body_html: str) -> tuple[bool, str | None]:
        if not self.api_key:
            return False, "Resend transport selected but api_key is empty"
        try:
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": self.sender,
                    "to": [to_addr],
                    "subject": subject,
                    "html": body_html,
                },
                timeout=self.request_timeout,
            )
        except requests.RequestException as e:
            return False, f"network error: {e}"

        if not resp.ok:
            return False, f"HTTP {resp.status_code} {resp.text[:200]}"
        return True, None

    def _send_smtp(self, to_addr: str, subject: str, body_html: str) -> tuple[bool, str | None]:
        host = os.environ.get("SMTP_HOST")
        port = int(os.environ.get("SMTP_PORT", "587"))
        user = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")
        if not all([host, user, password]):
            return False, "SMTP transport requires SMTP_HOST/SMTP_USER/SMTP_PASSWORD env vars"

        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content("Your mail client does not support HTML.")
        msg.add_alternative(body_html, subtype="html")

        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(host, port, timeout=self.request_timeout) as server:
                server.starttls(context=ctx)
                server.login(user, password)
                server.send_message(msg)
        except Exception as e:
            return False, f"smtp error: {e}"
        return True, None
