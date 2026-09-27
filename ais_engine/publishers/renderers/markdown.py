"""Telegram MarkdownV2 renderer.

Telegram's MarkdownV2 dialect requires a specific set of characters to be
escaped wherever they appear outside formatting entities. The set per the
docs is::

    _ * [ ] ( ) ~ ` > # + - = | { } . !

The renderer:
- Treats each AlphaSignal body (already a normalized 5-module string) as
  plain text to escape;
- Bolds the 5 module labels for visual hierarchy;
- Auto-links bare URLs (the 信源链接 / Source line) so users can tap them;
- Joins multiple signals with a thin horizontal separator;
- Splits the final output by the Telegram 4096-char message limit, never
  cutting mid-signal.

Reference: https://core.telegram.org/bots/api#markdownv2-style
"""

from __future__ import annotations

import re

from models import AlphaSignal, Subscriber
from publishers.renderers.base import BaseRenderer


_MD2_SPECIALS = r"_*[]()~`>#+-=|{}.!\\"
_MD2_ESCAPE_RE = re.compile(f"([{re.escape(_MD2_SPECIALS)}])")

# Five-module labels in both languages. Keys are matched at line start
# (after the inevitable single newline produced by ``format_five_modules_multiline``).
_MODULE_LABELS_ZH = ("破局信号", "Alpha评分", "核心洞察", "深度推演", "信源链接")
_MODULE_LABELS_EN = ("Headline", "Alpha Score", "Core Insight", "Forward View", "Source")

_URL_RE = re.compile(r"(https?://[^\s)]+)")

# Labels that constitute the "source link" module across both languages —
# free-mode renderers drop these lines entirely.
_SOURCE_LABELS = ("信源链接", "Source")


def _escape_md2(text: str) -> str:
    return _MD2_ESCAPE_RE.sub(r"\\\1", text)


def _format_one_signal(body: str, *, mode: str = "free") -> str:
    """Convert a normalized 5-module body into MarkdownV2.

    ``mode="free"`` drops the 【信源链接】 / [Source] line entirely (per
    v0.1 product spec: free tier gets headline + insight + forward view +
    score, no source). ``mode="paid"`` (v0.2+) keeps all five modules.
    """
    lines_out: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        label, rest = _split_label(line)
        if label in _SOURCE_LABELS and mode == "free":
            continue
        if label:
            # Hyperlink the source URL when present, plain-escape otherwise.
            urls = _URL_RE.findall(rest)
            if urls:
                url = urls[0]
                escaped_url = url.replace(")", r"\)")
                # Keep URL human-readable as the link text; subscribers tap to open.
                bold_label = f"*{_escape_md2(label)}*"
                lines_out.append(f"{bold_label}: [{_escape_md2(url)}]({escaped_url})")
            else:
                lines_out.append(f"*{_escape_md2(label)}*: {_escape_md2(rest)}")
        else:
            lines_out.append(_escape_md2(line))
    return "\n".join(lines_out)


def _split_label(line: str) -> tuple[str | None, str]:
    """Return ``(label, rest)`` if the line starts with a recognized module
    label, else ``(None, line)``."""
    for label in _MODULE_LABELS_ZH:
        prefix = f"【{label}】:"
        if line.startswith(prefix):
            return label, line[len(prefix):].strip()
        prefix = f"【{label}】："
        if line.startswith(prefix):
            return label, line[len(prefix):].strip()
    for label in _MODULE_LABELS_EN:
        prefix = f"[{label}]:"
        if line.startswith(prefix):
            return label, line[len(prefix):].strip()
    return None, line


# U+2501 BOX DRAWINGS HEAVY HORIZONTAL is not a MarkdownV2 special, so it
# passes through untouched and looks like a clean hairline divider.
_SEPARATOR = "\n\n━━━━━━━━━━\n\n"


class MarkdownRenderer(BaseRenderer):
    """Telegram MarkdownV2 renderer with per-message length splitting.

    ``mode`` controls source-link exposure (see ``_format_one_signal``).
    Default is ``"free"`` to match v0.1 free-tier behavior.
    """

    def __init__(self, max_chars: int = 4096, mode: str = "free") -> None:
        self.max_chars = max_chars
        self.mode = mode

    def render(self, signals: list[AlphaSignal], subscriber: Subscriber) -> list[str]:
        # Renderer-level mode is the default; a paid subscriber overrides it
        # so we can run a single renderer instance across mixed audiences.
        mode = "paid" if subscriber.tier == "paid" else self.mode

        formatted: list[str] = []
        for sig in signals:
            body = sig.body_for(subscriber.lang)  # type: ignore[arg-type]
            if not body:
                continue
            md = _format_one_signal(body, mode=mode)
            if md:
                formatted.append(md)
        if not formatted:
            return []

        return self._batch(formatted)

    def _batch(self, parts: list[str]) -> list[str]:
        out: list[str] = []
        current = ""
        for part in parts:
            candidate = part if not current else f"{current}{_SEPARATOR}{part}"
            if len(candidate) <= self.max_chars:
                current = candidate
                continue
            if current:
                out.append(current)
                current = part
            else:
                # Single signal exceeds the message budget — hard truncate
                # the body but keep the message valid MD2 (ellipsis).
                out.append(part[: self.max_chars - 1] + "…")
                current = ""
        if current:
            out.append(current)
        return out
