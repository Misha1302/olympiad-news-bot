from __future__ import annotations

import re


class InvalidClassifierResponse(ValueError):
    pass


def remove_non_bmp_chars(text: str) -> str:
    if not text:
        return text

    text = re.sub(r"[\U00010000-\U0010FFFF]", "", text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)
    return text.strip()


def normalize_classifier_text(text: str, max_chars: int) -> str:
    cleaned = remove_non_bmp_chars(text)
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_chars]


def parse_binary_answer(answer: str) -> bool:
    normalized = answer.strip().casefold().rstrip(".!\"'")

    if normalized in {"да", "yes"}:
        return True
    if normalized in {"нет", "no"}:
        return False

    raise InvalidClassifierResponse(
        f"Expected an exact binary answer, got: {answer!r}"
    )
