"""Reconstructed Telegram transport; not enabled by recovery."""
import requests
from publishers.base import BasePublisher, DeliveryResult
from publishers.renderers.markdown import MarkdownRenderer

class TelegramPublisher(BasePublisher):
    channel = "telegram"

    def __init__(self, bot_token, max_chars=4096):
        self.bot_token = bot_token
        self.renderer = MarkdownRenderer(max_chars=max_chars)

    def publish(self, signals, subscribers, *, dry_run=False):
        results = []
        for sub in subscribers:
            if sub.channel != self.channel:
                continue
            messages = self.renderer.render(signals, sub)
            error = None
            if not dry_run:
                for message in messages:
                    try:
                        response = requests.post(
                            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                            json={"chat_id": sub.address, "text": message, "parse_mode": "MarkdownV2"}, timeout=15)
                        if not response.ok or not response.json().get("ok"):
                            error = "Telegram rejected message"
                            break
                    except (requests.RequestException, ValueError):
                        error = "Telegram transport failed"
                        break
            results.append(DeliveryResult(subscriber_id=sub.id, signal_ids=[s.id for s in signals],
                success=error is None, error=error, dry_run=dry_run,
                payload_preview='\n'.join(messages)[:200]))
        return results
