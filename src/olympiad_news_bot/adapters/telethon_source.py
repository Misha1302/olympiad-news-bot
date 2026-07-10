from __future__ import annotations

import logging
from typing import Any

from telethon import TelegramClient, events
from telethon.errors import PhoneNumberInvalidError, SessionPasswordNeededError

from ..domain import IncomingMessage
from ..ports import MessageHandler

LOGGER = logging.getLogger(__name__)


class TelethonMessageSource:
    def __init__(
        self,
        client: TelegramClient,
        channels: tuple[str, ...],
    ) -> None:
        self._client = client
        self._channels = channels

    async def run(self, handler: MessageHandler) -> None:
        await self._client.connect()
        try:
            if not await self._authorize_user():
                raise RuntimeError("Telegram authorization failed")

            await self._validate_channels()

            @self._client.on(events.NewMessage(chats=self._channels))
            async def on_new_message(event: Any) -> None:
                message = await self._translate_event(event)
                if message is not None:
                    await handler(message)

            LOGGER.info("Monitoring started for %d channels", len(self._channels))
            await self._client.run_until_disconnected()
        finally:
            await self._client.disconnect()

    async def _authorize_user(self) -> bool:
        if await self._client.is_user_authorized():
            return True

        try:
            phone = input("Введите номер телефона с кодом страны: ")
            await self._client.send_code_request(phone)
            code = input("Введите код из Telegram: ")
            try:
                await self._client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("Введите пароль двухэтапной аутентификации: ")
                await self._client.sign_in(password=password)
            return True
        except PhoneNumberInvalidError:
            LOGGER.error("Invalid Telegram phone number")
            return False
        except Exception:
            LOGGER.exception("Telegram authorization failed")
            return False

    async def _validate_channels(self) -> None:
        for channel in self._channels:
            try:
                await self._client.get_entity(channel)
                LOGGER.info("Connected to %s", channel)
            except Exception:
                LOGGER.exception("Cannot connect to %s", channel)

    @staticmethod
    async def _translate_event(event: Any) -> IncomingMessage | None:
        text = event.message.text or event.message.message
        if not text or not text.strip():
            return None

        chat = await event.get_chat()
        if getattr(chat, "username", None):
            source_name = f"@{chat.username}"
        elif getattr(chat, "title", None):
            source_name = str(chat.title)
        else:
            source_name = f"ID: {chat.id}"

        return IncomingMessage(
            source_id=str(chat.id),
            source_name=source_name,
            message_id=event.message.id,
            text=text,
        )
