"""On-demand translation with file-system cache.

Strategy (per plan §三):
- Signals are generated in their source language only.
- At publish time, for each (signal_id, target_lang) pair we check the cache
  on disk first; on miss we call Gemini Flash with a 5-module-preserving
  prompt and write the result back to cache.
- The cache key is content-agnostic — if you mutate ``bodies[source_lang]``
  you must clear ``data/translations/{signal_id}__{lang}.txt``.

The implementation is intentionally synchronous; concurrency lives in the
orchestrator if/when we batch translations across subscribers.
"""

from __future__ import annotations

import os
from typing import Optional

from generators.gemini import GeminiClient
from models import AlphaSignal, Language
from utils.logger import get_logger

logger = get_logger(__name__)


_DEFAULT_PROMPT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "generators",
    "prompts",
)


def _load_prompt(src: str, dst: str) -> str:
    """Load the translate prompt for ``src→dst``. Falls back to a generic
    instruction if no template file is present (defensive — Phase 3 ships
    the templates but a user might delete one)."""
    fname = f"translate_{src}_to_{dst}.txt"
    path = os.path.join(_DEFAULT_PROMPT_DIR, fname)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return (
        f"Translate the following AIS signal from {src} to {dst}. "
        "Preserve the 5-module structure (Headline / Alpha Score / Core "
        "Insight / Forward View / Source) and length ratio 1:2:4. Do not "
        "add commentary. Output only the translated body.\n\nInput:\n{body}"
    )


class Translator:
    def __init__(
        self,
        client: Optional[GeminiClient] = None,
        cache_dir: str = "data/translations",
    ) -> None:
        self.client = client
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    # -------------------------------------------------------------------- #
    # Public
    # -------------------------------------------------------------------- #

    def ensure(self, signal: AlphaSignal, target_lang: Language) -> Optional[str]:
        """Populate ``signal.bodies[target_lang]`` and return the body.

        Returns the cached/freshly-translated body, or ``None`` if neither
        cache nor LLM produced anything (e.g. missing client + cache miss).
        """
        if signal.bodies.get(target_lang):
            return signal.bodies[target_lang]

        cached = self._read_cache(signal.id, target_lang)
        if cached:
            signal.bodies[target_lang] = cached
            return cached

        src_body = signal.bodies.get(signal.source_lang)
        if not src_body:
            logger.warning(f"Translator: signal {signal.id} has no source body to translate.")
            return None

        if self.client is None:
            logger.info(f"Translator: client absent, cannot translate signal {signal.id} on miss.")
            return None

        translated = self._call_llm(src_body, signal.source_lang, target_lang)
        if not translated:
            return None

        self._write_cache(signal.id, target_lang, translated)
        signal.bodies[target_lang] = translated
        return translated

    # -------------------------------------------------------------------- #
    # Internals
    # -------------------------------------------------------------------- #

    def _cache_path(self, signal_id: str, lang: str) -> str:
        return os.path.join(self.cache_dir, f"{signal_id}__{lang}.txt")

    def _read_cache(self, signal_id: str, lang: str) -> Optional[str]:
        path = self._cache_path(signal_id, lang)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip() or None
        except Exception as e:
            logger.warning(f"Translator: cache read failed for {path}: {e}")
            return None

    def _write_cache(self, signal_id: str, lang: str, text: str) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)
        path = self._cache_path(signal_id, lang)
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)
        except Exception as e:
            logger.warning(f"Translator: cache write failed for {path}: {e}")

    def _call_llm(self, body: str, src: str, dst: str) -> Optional[str]:
        assert self.client is not None
        prompt_template = _load_prompt(src, dst)
        prompt = prompt_template.replace("{body}", body) if "{body}" in prompt_template else (
            prompt_template + "\n\nInput:\n" + body
        )
        # Reuse the cheap scorer model — translation is short, low-reasoning.
        result = self.client._call_gemini(  # noqa: SLF001 — intentional reuse
            "gemini-3-flash-preview",
            prompt,
            timeout_sec=self.client.score_timeout_sec,
            max_retries=self.client.score_max_retries,
        )
        if not result:
            logger.error(f"Translator: LLM returned nothing for {src}→{dst}")
        return result
