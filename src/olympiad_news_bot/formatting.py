from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from .domain import IncomingMessage, Notification

MAX_TELEGRAM_MESSAGE_LENGTH = 4096


def split_text_for_telegram(
    text: str,
    max_length: int = MAX_TELEGRAM_MESSAGE_LENGTH,
) -> list[str]:
    if max_length <= 0:
        raise ValueError("max_length must be positive")
    if len(text) <= max_length:
        return [text]

    parts: list[str] = []
    remaining = text
    while len(remaining) > max_length:
        split_at = remaining.rfind("\n", 1, max_length + 1)
        if split_at > 0:
            split_at += 1
        else:
            split_at = remaining.rfind(" ", 1, max_length + 1)
            if split_at <= 0:
                split_at = max_length

        parts.append(remaining[:split_at])
        remaining = remaining[split_at:]

    if remaining:
        parts.append(remaining)
    return parts


def format_source(channel_name: str, message_id: int) -> str:
    if channel_name.startswith("@"):
        return f"{channel_name}: https://t.me/{channel_name[1:]}/{message_id}"
    return channel_name


class TelegramNotificationFormatter:
    def __init__(self, clock: Callable[[], datetime] = datetime.now) -> None:
        self._clock = clock

    def format(self, message: IncomingMessage) -> Notification:
        source = format_source(message.source_name, message.message_id)
        text = (
            "НОВОСТЬ ОБ ОЛИМПИАДЕ\n\n"
            f"{message.text}\n\n"
            f"Источник: {source}\n"
            f"Время: {self._clock().strftime('%H:%M %d.%m.%Y')}\n\n"
            "#олимпиада #программирование"
        )
        return Notification(source_key=message.source_key, text=text)
