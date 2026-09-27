import re


MODULES = ["破局信号", "Alpha评分", "核心洞察", "深度推演", "信源链接"]


def normalize_alpha_text(text: str) -> str:
    normalized = str(text).replace("\r", " ").replace("\n", " ")
    normalized = re.sub(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>.*?</a>',
        r"\1",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r"\[[^\]]+\]\((https?://[^)]+)\)", r"\1", normalized)
    normalized = normalized.replace("**", "")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def format_five_modules_multiline(text: str) -> str:
    formatted = normalize_alpha_text(text)
    for name in MODULES:
        formatted = re.sub(rf"\s*【{name}】\s*:\s*", f"\n【{name}】: ", formatted)
    return formatted.strip()
