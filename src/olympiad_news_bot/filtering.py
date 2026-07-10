from __future__ import annotations

from collections.abc import Iterable

from .classification import remove_non_bmp_chars


DEFAULT_KEYWORDS = (
    "регистрация",
    "началась",
    "олимпиад",
    "результат",
    "отбор",
    "соревновани",
    "программир",
    "contest",
    "раунд",
    "round",
    "турнир",
    "чемпионат",
    "старт",
    "запуск",
    "объявление",
    "анонс",
    "победитель",
    "призер",
    "призёр",
    "финал",
    "задача",
    "задачи",
    "решение",
    "итоги",
    "результаты",
)

DEFAULT_PLATFORMS = (
    "codeforces",
    "acmp",
    "e-olymp",
    "yandex",
    "timus",
    "informatics",
    "acm",
    "icpc",
    "шаг в будущее",
    "иннополис",
    "открытая олимпиада",
    "высшая проба",
    "ломоносов",
    "изумруд",
    "технокубок",
    "когнитивные",
    "росатом",
    "гранит науки",
    "бельчонок",
    "всесибирская",
    "мош",
    "московская олимпиада школьников",
    "спбгу",
    "санкт-петербургского",
    "всерос",
    "всероссийск",
    "международн",
)


class KeywordPrefilter:
    def __init__(
        self,
        keywords: Iterable[str] = DEFAULT_KEYWORDS,
        platforms: Iterable[str] = DEFAULT_PLATFORMS,
        minimum_text_length: int = 10,
    ) -> None:
        self._keywords = tuple(item.casefold() for item in keywords)
        self._platforms = tuple(item.casefold() for item in platforms)
        self._minimum_text_length = minimum_text_length

    def matches(self, text: str) -> bool:
        if not text or len(text.strip()) < self._minimum_text_length:
            return False

        normalized = remove_non_bmp_chars(text).casefold()
        return any(item in normalized for item in self._keywords) or any(
            item in normalized for item in self._platforms
        )
