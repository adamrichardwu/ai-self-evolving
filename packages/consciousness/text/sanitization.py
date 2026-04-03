import re
from collections.abc import Mapping, Sequence
from typing import Any


def contains_cjk(text: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in text)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_mixed_spacing(text: str) -> str:
    normalized = normalize_whitespace(text)
    if not normalized:
        return ""
    normalized = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", normalized)
    normalized = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[，。！？；：,.!?;:])", "", normalized)
    normalized = re.sub(r"(?<=[，。！？；：,.!?;:])\s+(?=[\u4e00-\u9fff])", "", normalized)
    return normalized


def normalize_repeat_key(text: str) -> str:
    return "".join(character.casefold() for character in normalize_mixed_spacing(text) if character.isalnum())


def split_text_units(text: str) -> list[str]:
    normalized = normalize_mixed_spacing(text)
    if not normalized:
        return []
    units = [
        unit.strip()
        for unit in re.findall(r"[^。！？.!?;；\n]+(?:[。！？.!?;；]+)?", normalized)
        if unit.strip()
    ]
    return units or [normalized]


def dedupe_text_units(units: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for unit in units:
        key = normalize_repeat_key(unit)
        if not key:
            continue
        if deduped and key == normalize_repeat_key(deduped[-1]):
            continue
        if key in seen and len(units) > 1:
            continue
        deduped.append(unit)
        seen.add(key)
    return deduped


def join_text_units(units: list[str]) -> str:
    cleaned_units = [unit.strip() for unit in units if unit.strip()]
    if not cleaned_units:
        return ""
    if any(contains_cjk(unit) for unit in cleaned_units):
        return "".join(cleaned_units)
    return " ".join(cleaned_units)


def truncate_text(text: str, max_length: int) -> str:
    normalized = normalize_mixed_spacing(text)
    if len(normalized) <= max_length:
        return normalized
    truncated = normalized[: max_length - 3].rstrip(" ,，;；")
    return f"{truncated}..."


def limit_text_units(units: list[str], max_length: int) -> str:
    limited: list[str] = []
    for unit in units:
        candidate = join_text_units([*limited, unit])
        if limited and len(candidate) > max_length:
            break
        limited.append(unit)
        if len(candidate) >= max_length:
            break
    return join_text_units(limited)


def limit_thought_sentences(units: list[str], max_sentences: int, max_length: int) -> str:
    limited = units[:max_sentences]
    while limited:
        joined = join_text_units(limited)
        if len(joined) <= max_length:
            return joined
        limited = limited[:-1]
    return ""


def sanitize_focus_text(text: str, fallback: str) -> str:
    units = dedupe_text_units(split_text_units(text))
    focus = units[0] if units else normalize_mixed_spacing(fallback)
    focus = truncate_text(focus, 120).strip(" .,!?:;，。！？；：")
    if focus:
        return focus
    fallback_focus = truncate_text(normalize_mixed_spacing(fallback), 120).strip(" .,!?:;，。！？；：")
    return fallback_focus or "maintain coherent interaction"


def sanitize_thought_text(text: str, fallback_text: str, previous_text: str = "") -> str:
    units = dedupe_text_units(split_text_units(text))
    cleaned = limit_thought_sentences(units, max_sentences=3, max_length=280)
    if not cleaned:
        cleaned = limit_text_units(units, 280) or truncate_text(join_text_units(units), 280)
    previous_key = normalize_repeat_key(previous_text)
    if cleaned and previous_key and normalize_repeat_key(cleaned) == previous_key:
        cleaned = ""
    if cleaned:
        return cleaned

    fallback_units = dedupe_text_units(split_text_units(fallback_text))
    fallback = limit_thought_sentences(fallback_units, max_sentences=3, max_length=280)
    if not fallback:
        fallback = limit_text_units(fallback_units, 280) or truncate_text(join_text_units(fallback_units), 280)
    return fallback or truncate_text(normalize_mixed_spacing(fallback_text), 280)


def sanitize_nested_text(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_mixed_spacing(value)
    if isinstance(value, Mapping):
        return {key: sanitize_nested_text(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [sanitize_nested_text(item) for item in value]
    return value