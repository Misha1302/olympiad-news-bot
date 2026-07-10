from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Iterable
from typing import Protocol

from .domain import DeliveryFailure, DeliveryReport, Notification
from .formatting import split_text_for_telegram


class TelegramBotClient(Protocol):
    def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        disable_web_page_preview: bool,
    ) -> object:
        ...


class DeliveryReceiptStore(Protocol):
    def was_delivered(self, source_key: str, chat_id: str, part_index: int) -> bool:
        ...

    def mark_delivered(self, source_key: str, chat_id: str, part_index: int) -> None:
        ...


class NullDeliveryReceiptStore:
    def was_delivered(self, source_key: str, chat_id: str, part_index: int) -> bool:
        return False

    def mark_delivered(self, source_key: str, chat_id: str, part_index: int) -> None:
        return None


class TelegramNotificationSink:
    def __init__(
        self,
        bot: TelegramBotClient,
        chat_ids: Iterable[str],
        max_retries: int = 3,
        receipt_store: DeliveryReceiptStore | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        normalized_chat_ids = tuple(
            str(chat_id).strip() for chat_id in chat_ids if str(chat_id).strip()
        )
        if not normalized_chat_ids:
            raise ValueError("At least one destination chat is required")
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1")

        self._bot = bot
        self._chat_ids = normalized_chat_ids
        self._max_retries = max_retries
        self._receipt_store = receipt_store or NullDeliveryReceiptStore()
        self._sleep = sleep

    async def send(self, notification: Notification) -> DeliveryReport:
        parts = split_text_for_telegram(notification.text)
        attempted = len(self._chat_ids) * len(parts)
        delivered = 0
        failures: list[DeliveryFailure] = []

        for chat_id in self._chat_ids:
            for part_index, part in enumerate(parts):
                already_delivered = await asyncio.to_thread(
                    self._receipt_store.was_delivered,
                    notification.source_key,
                    chat_id,
                    part_index,
                )
                if already_delivered:
                    delivered += 1
                    continue

                error = await asyncio.to_thread(
                    self._send_part_with_retry,
                    chat_id,
                    part,
                )
                if error is None:
                    await asyncio.to_thread(
                        self._receipt_store.mark_delivered,
                        notification.source_key,
                        chat_id,
                        part_index,
                    )
                    delivered += 1
                else:
                    failures.append(
                        DeliveryFailure(
                            chat_id=chat_id,
                            part_index=part_index,
                            error=str(error),
                        )
                    )
                    # Preserve part ordering for this destination. A later retry can
                    # resume from the first unrecorded part using the receipt store.
                    break

        return DeliveryReport(
            attempted=attempted,
            delivered=delivered,
            failures=tuple(failures),
        )

    def _send_part_with_retry(self, chat_id: str, part: str) -> Exception | None:
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                self._bot.send_message(
                    chat_id,
                    part,
                    disable_web_page_preview=True,
                )
                return None
            except Exception as error:  # external client errors are adapter concerns
                last_error = error
                if attempt < self._max_retries - 1:
                    self._sleep(2**attempt)
        return last_error
