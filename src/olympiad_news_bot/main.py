from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import telebot
from telethon import TelegramClient

from .adapters.gigachat import GigaChatClassifier
from .adapters.sqlite_receipts import SqliteDeliveryReceiptStore
from .adapters.telethon_source import TelethonMessageSource
from .application import NewsProcessor
from .config import Settings, load_settings
from .delivery import TelegramNotificationSink
from .filtering import KeywordPrefilter
from .formatting import TelegramNotificationFormatter
from .queueing import MessageQueue
from .runtime import BotRuntime


def build_runtime(settings: Settings) -> BotRuntime:
    Path(".runtime").mkdir(parents=True, exist_ok=True)

    telegram_client = TelegramClient(
        ".runtime/user_session",
        settings.telegram.api_id,
        settings.telegram.api_hash,
    )
    bot_client = telebot.TeleBot(settings.telegram.bot_token)

    classifier = (
        GigaChatClassifier(settings.gigachat)
        if settings.gigachat.enabled
        else None
    )
    receipt_store = SqliteDeliveryReceiptStore(
        settings.runtime.delivery_receipt_db_path
    )
    sink = TelegramNotificationSink(
        bot=bot_client,
        chat_ids=settings.telegram.destination_chat_ids,
        max_retries=settings.telegram.send_max_retries,
        receipt_store=receipt_store,
    )
    processor = NewsProcessor(
        prefilter=KeywordPrefilter(),
        classifier=classifier,
        formatter=TelegramNotificationFormatter(),
        sink=sink,
        fail_open=settings.gigachat.fail_open,
    )
    source = TelethonMessageSource(
        client=telegram_client,
        channels=settings.telegram.monitor_channels,
    )
    queue = MessageQueue(max_queue_size=settings.runtime.queue_size)
    return BotRuntime(source=source, processor=processor, queue=queue)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    runtime = build_runtime(load_settings())
    try:
        asyncio.run(runtime.run())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Bot stopped by user")


if __name__ == "__main__":
    main()
