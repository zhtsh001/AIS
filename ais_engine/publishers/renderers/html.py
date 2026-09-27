"""Reconstructed email renderer compatible with the recovered publisher."""
from html import escape
from urllib.parse import urlencode
from publishers.renderers.base import BaseRenderer
from publishers.renderers.markdown import _split_label

def render_subject(lang, count):
    return f"AIS 情报简报 · {count} 条" if lang == "zh" else f"AIS Intelligence Digest · {count} signals"

class HTMLRenderer(BaseRenderer):
    def __init__(self, mode="free", cadence_label="daily", public_origin=None):
        self.mode = mode
        self.cadence_label = cadence_label
        self.public_origin = public_origin

    def render(self, signals, subscriber):
        if not signals:
            return []
        sections = []
        mode = "paid" if subscriber.tier == "paid" else self.mode
        for lang in dict.fromkeys(subscriber.langs or ["zh"]):
            sections.append(f"<h2>{escape(lang)}</h2>")
            for signal in signals:
                lines = []
                for line in (signal.body_for(lang) or "").splitlines():
                    label, _ = _split_label(line.strip())
                    if mode == "free" and label in ("Source", "信源链接"):
                        continue
                    if line.strip():
                        lines.append(f"<p>{escape(line)}</p>")
                if lines:
                    sections.append('<section style="margin-bottom:24px">' + ''.join(lines) + '</section>')
        footer = "AIS automated digest. Reply unsubscribe to opt out."
        if self.public_origin and subscriber.unsubscribe_token:
            url = self.public_origin.rstrip('/') + '/unsubscribe?' + urlencode({'token': subscriber.unsubscribe_token})
            footer = f'<a href="{escape(url, quote=True)}">Unsubscribe / 退订</a>'
        title = escape(render_subject(subscriber.lang, len(signals)))
        return [f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head><body><h1>{title}</h1>' + ''.join(sections) + f'<footer>{footer}</footer></body></html>']
