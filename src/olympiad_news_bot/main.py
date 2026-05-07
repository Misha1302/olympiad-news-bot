import asyncio
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from typing import Any

import requests
import telebot
import urllib3
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import PhoneNumberInvalidError, SessionPasswordNeededError

load_dotenv()

SECRET_NAMES = (
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_BOT_TOKEN",
    "IDS_TO_CHAT",
    "MONITOR_CHANNELS",
    "GIGACHAT_ENABLED",
    "GIGACHAT_AUTH_KEY",
    "GIGACHAT_SCOPE",
    "GIGACHAT_MODEL",
    "GIGACHAT_VERIFY_SSL",
    "GIGACHAT_TIMEOUT_SECONDS",
    "GIGACHAT_MAX_RETRIES",
    "GIGACHAT_FAIL_OPEN",
    "GIGACHAT_MAX_TEXT_CHARS",
)

DEFAULT_MONITOR_CHANNELS = [
    "@codeforces_official",
    "@olymp_bmstu",
    "@olymp_itmo11",
    "@InfMosh",
    "@olympspbu",
    "@telemathus",
    "@openolymp",
    "@cotecholymp",
    "@sbornik_olprog",
    "@t_prod",
    "@olymp_mephi",
    "@matolimp",
    "@vsesib_olymp",
    "@bvimethod",
    "@postupashki",
]

KEYWORDS = [
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
]

PLATFORMS = [
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
]

TELEGRAM_MESSAGE_LIMIT = 4096
SAFE_TELEGRAM_MESSAGE_LIMIT = 4000
CONTROL_CHARS_EXCEPT_NEWLINES_AND_TAB = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
AUTHORIZATION_HEADER = "Author" + "ization"
BASIC_PREFIX = "Basic"
BEARER_PREFIX = "Bearer"


class ConfigurationError(RuntimeError):
    pass


def load_local_secrets() -> dict[str, Any]:
    for module_name in ("SECRETS", "olympiad_news_bot.SECRETS"):
        try:
            module = import_module(module_name)
        except ModuleNotFoundError as error:
            if error.name == module_name:
                continue
            raise

        return {
            name: getattr(module, name)
            for name in SECRET_NAMES
            if hasattr(module, name)
        }

    return {}


LOCAL_SECRETS = load_local_secrets()


def stringify_config_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (list, tuple, set)):
        return ",".join(str(item).strip() for item in value if str(item).strip())

    return str(value).strip()


def read_config(name: str, default: Any = "") -> str:
    if name in LOCAL_SECRETS:
        return stringify_config_value(LOCAL_SECRETS[name])

    return stringify_config_value(os.getenv(name, default))


def read_required_config(name: str) -> str:
    value = read_config(name)
    if not value:
        raise ConfigurationError(f"Configuration value {name} is required")
    return value


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def normalize_telegram_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return CONTROL_CHARS_EXCEPT_NEWLINES_AND_TAB.sub("", text).strip()


def split_telegram_text(text: str, limit: int = SAFE_TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if not text:
        return []

    if limit <= 0 or limit > TELEGRAM_MESSAGE_LIMIT:
        raise ValueError("Telegram message limit must be between 1 and 4096")

    return [text[start:start + limit] for start in range(0, len(text), limit)]


@dataclass(frozen=True)
class Settings:
    telegram_api_id: int
    telegram_api_hash: str
    telegram_bot_token: str
    ids_to_chat: list[str]
    monitor_channels: list[str]
    gigachat_enabled: bool
    gigachat_auth_key: str | None
    gigachat_scope: str
    gigachat_model: str
    gigachat_verify_ssl: bool
    gigachat_timeout_seconds: int
    gigachat_max_retries: int
    gigachat_fail_open: bool
    gigachat_max_text_chars: int

    @staticmethod
    def load() -> "Settings":
        ids_to_chat = parse_csv(read_required_config("IDS_TO_CHAT"))
        if not ids_to_chat:
            raise ConfigurationError("IDS_TO_CHAT must contain at least one chat ID")

        gigachat_enabled = parse_bool(read_config("GIGACHAT_ENABLED", "true"), default=True)
        gigachat_auth_key = read_config("GIGACHAT_AUTH_KEY") or None
        if gigachat_enabled and not gigachat_auth_key:
            raise ConfigurationError(
                "GIGACHAT_AUTH_KEY is required when GIGACHAT_ENABLED=true. "
                "Set GIGACHAT_ENABLED=false to use only keyword filtering."
            )

        return Settings(
            telegram_api_id=int(read_required_config("TELEGRAM_API_ID")),
            telegram_api_hash=read_required_config("TELEGRAM_API_HASH"),
            telegram_bot_token=read_required_config("TELEGRAM_BOT_TOKEN"),
            ids_to_chat=ids_to_chat,
            monitor_channels=parse_csv(read_config("MONITOR_CHANNELS")) or DEFAULT_MONITOR_CHANNELS,
            gigachat_enabled=gigachat_enabled,
            gigachat_auth_key=gigachat_auth_key,
            gigachat_scope=read_config("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
            gigachat_model=read_config("GIGACHAT_MODEL", "GigaChat"),
            gigachat_verify_ssl=parse_bool(read_config("GIGACHAT_VERIFY_SSL", "true"), default=True),
            gigachat_timeout_seconds=int(read_config("GIGACHAT_TIMEOUT_SECONDS", "30")),
            gigachat_max_retries=int(read_config("GIGACHAT_MAX_RETRIES", "3")),
            gigachat_fail_open=parse_bool(read_config("GIGACHAT_FAIL_OPEN", "true"), default=True),
            gigachat_max_text_chars=int(read_config("GIGACHAT_MAX_TEXT_CHARS", "5000")),
        )


class GigaChatClassifier:
    OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    CHAT_COMPLETIONS_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._access_token: str | None = None
        self._access_token_expires_at_ms = 0
        self._lock = threading.Lock()

        if not settings.gigachat_verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def check_message(self, text: str) -> bool:
        with self._lock:
            last_error: Exception | None = None
            for attempt in range(1, self.settings.gigachat_max_retries + 1):
                try:
                    result = self._classify(text)
                    print(f"GigaChat decision: {'SEND' if result else 'SKIP'}")
                    return result
                except Exception as error:
                    last_error = error
                    print(f"GigaChat check failed, attempt {attempt}: {error}")
                    if attempt < self.settings.gigachat_max_retries:
                        time.sleep(2 ** (attempt - 1))

            raise RuntimeError(f"GigaChat check failed after retries: {last_error}")

    def _classify(self, text: str) -> bool:
        prompt_text = normalize_telegram_text(text)
        prompt_text = re.sub(r"\s+", " ", prompt_text).strip()
        prompt_text = prompt_text[: self.settings.gigachat_max_text_chars]

        response = requests.post(
            self.CHAT_COMPLETIONS_URL,
            headers={
                AUTHORIZATION_HEADER: f"{BEARER_PREFIX} {self._get_access_token()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "model": self.settings.gigachat_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты строгий бинарный классификатор Telegram-сообщений. "
                            "Не объясняй ответ. Не добавляй Markdown. Верни только ДА или НЕТ."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Определи, относится ли сообщение к новостям, анонсам, срокам регистрации, "
                            "итогам или результатам олимпиад, соревнований по программированию, математике "
                            "или инженерным конкурсам для школьников/студентов. "
                            "Ответь строго одним словом: ДА или НЕТ.\n\n"
                            f"Сообщение: {prompt_text}"
                        ),
                    },
                ],
                "temperature": 0,
                "max_tokens": 8,
            },
            timeout=self.settings.gigachat_timeout_seconds,
            verify=self.settings.gigachat_verify_ssl,
        )

        if response.status_code == 401:
            self._drop_access_token()
            return self._classify(text)

        response.raise_for_status()
        return self._parse_answer(response.json())

    def _get_access_token(self) -> str:
        now_ms = int(time.time() * 1000)
        if self._access_token and self._access_token_expires_at_ms > now_ms + 60_000:
            return self._access_token

        response = requests.post(
            self.OAUTH_URL,
            headers={
                AUTHORIZATION_HEADER: self._build_basic_auth_header(),
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"scope": self.settings.gigachat_scope},
            timeout=self.settings.gigachat_timeout_seconds,
            verify=self.settings.gigachat_verify_ssl,
        )
        response.raise_for_status()

        data = response.json()
        self._access_token = str(data.get("access_token", "")).strip()
        if not self._access_token:
            raise RuntimeError("GigaChat OAuth response does not contain access_token")

        expires_at = data.get("expires_at")
        self._access_token_expires_at_ms = int(expires_at) if expires_at else int((time.time() + 25 * 60) * 1000)
        return self._access_token

    def _drop_access_token(self) -> None:
        self._access_token = None
        self._access_token_expires_at_ms = 0

    def _build_basic_auth_header(self) -> str:
        if not self.settings.gigachat_auth_key:
            raise ConfigurationError("GIGACHAT_AUTH_KEY is required")

        auth_key = self.settings.gigachat_auth_key.strip()
        if auth_key.lower().startswith(f"{BASIC_PREFIX.lower()} "):
            return auth_key

        return f"{BASIC_PREFIX} {auth_key}"

    @staticmethod
    def _parse_answer(response_json: dict[str, Any]) -> bool:
        try:
            answer = str(response_json["choices"][0]["message"]["content"]).strip().lower()
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected GigaChat response shape: {response_json}") from error

        normalized = answer.replace(".", "").replace("!", "").replace('"', "").replace("'", "")
        if normalized.startswith(("да", "yes")):
            return True

        if normalized.startswith(("нет", "no")):
            return False

        if any(word in normalized for word in ["не относится", "не связано", "нет"]):
            return False

        if any(word in normalized for word in ["олимп", "соревнован", "конкурс", "задач", "турнир", "чемпионат"]):
            return True

        raise RuntimeError(f"Cannot parse GigaChat answer as binary decision: {answer}")


class SimpleOlympiadBot:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ids_to_chat = settings.ids_to_chat
        self.monitor_channels = settings.monitor_channels
        self.user_client: TelegramClient | None = None
        self.bot: telebot.TeleBot | None = None
        self.gigachat_classifier = GigaChatClassifier(settings) if settings.gigachat_enabled else None
        self.check_count = 0

    def setup_clients(self) -> None:
        self.user_client = TelegramClient(
            ".runtime/user_session",
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
        )
        self.bot = telebot.TeleBot(self.settings.telegram_bot_token)

    async def authorize_user(self) -> bool:
        assert self.user_client is not None
        if await self.user_client.is_user_authorized():
            print("Telegram user is already authorized.")
            return True

        print("Telegram authorization is required.")
        try:
            phone = input("Введите номер телефона с кодом страны, например +79991234567: ")
            await self.user_client.send_code_request(phone)
            code = input("Введите код из Telegram: ")
            try:
                await self.user_client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("Введите пароль двухэтапной аутентификации: ")
                await self.user_client.sign_in(password=password)

            print("Telegram authorization completed.")
            return True
        except PhoneNumberInvalidError:
            print("Invalid phone number.")
            return False
        except Exception as error:
            print(f"Telegram authorization failed: {error}")
            return False

    def is_olympiad_related(self, text: str) -> bool:
        text_lower = normalize_telegram_text(text).lower()
        if len(text_lower) < 10:
            return False

        return any(keyword in text_lower for keyword in KEYWORDS) or any(platform in text_lower for platform in PLATFORMS)

    async def should_send_message(self, text: str) -> bool:
        self.check_count += 1
        print(f"Checking message #{self.check_count}")

        if not self.is_olympiad_related(text):
            print("Keyword prefilter: SKIP")
            return False

        print("Keyword prefilter: PASS")
        if not self.gigachat_classifier:
            print("GigaChat is disabled, using keyword prefilter only.")
            return True

        try:
            return await asyncio.to_thread(self.gigachat_classifier.check_message, text)
        except Exception as error:
            print(f"GigaChat failed: {error}")
            if self.settings.gigachat_fail_open:
                print("Fail-open mode is enabled: SEND because keyword prefilter passed.")
                return True

            print("Fail-open mode is disabled: SKIP.")
            return False

    def get_source_text(self, channel_name: str, message_id: int) -> str:
        if channel_name.startswith("@"):
            return f"{channel_name} — https://t.me/{channel_name[1:]}/{message_id}"

        return channel_name

    def format_message_parts(self, text: str, channel_name: str, message_id: int) -> list[str]:
        text = normalize_telegram_text(text)
        source_text = self.get_source_text(channel_name, message_id)
        timestamp = datetime.now().strftime("%H:%M %d.%m.%Y")

        message = (
            "НОВОСТЬ ОБ ОЛИМПИАДЕ\n\n"
            f"{text}\n\n"
            f"Источник: {source_text}\n"
            f"Время: {timestamp}\n\n"
            "#олимпиада #программирование"
        )

        if len(message) <= SAFE_TELEGRAM_MESSAGE_LIMIT:
            return [message]

        metadata = (
            "НОВОСТЬ ОБ ОЛИМПИАДЕ\n"
            f"Источник: {source_text}\n"
            f"Время: {timestamp}\n\n"
            "Текст длинный, поэтому отправлен без обрезки следующими сообщениями."
        )
        return [metadata, *split_telegram_text(text)]

    def send_notification_with_retry(self, text: str, channel_name: str, message_id: int) -> bool:
        assert self.bot is not None
        message_parts = self.format_message_parts(text, channel_name, message_id)

        for attempt in range(3):
            try:
                for chat_id in self.ids_to_chat:
                    for message_part in message_parts:
                        self.bot.send_message(
                            chat_id,
                            message_part,
                            disable_web_page_preview=True,
                        )

                return True
            except Exception as error:
                print(f"Notification send failed, attempt {attempt + 1}: {error}")
                if attempt < 2:
                    time.sleep(2 ** attempt)

        return False

    async def process_message(self, event: Any) -> None:
        text = event.message.text or event.message.message or ""
        if not text.strip():
            return

        chat = await event.get_chat()
        if getattr(chat, "username", None):
            channel_name = f"@{chat.username}"
        elif getattr(chat, "title", None):
            channel_name = chat.title
        else:
            channel_name = f"ID: {chat.id}"

        if await self.should_send_message(text):
            print(f"Sending olympiad news from {channel_name}: {text[:80]}")
            self.send_notification_with_retry(text, channel_name, event.message.id)
        else:
            print(f"Message skipped: {text[:80]}")

    async def start_monitoring_async(self) -> None:
        assert self.user_client is not None
        for channel in self.monitor_channels:
            try:
                await self.user_client.get_entity(channel)
                print(f"Connected to {channel}")
            except Exception as error:
                print(f"Cannot connect to {channel}: {error}")

        @self.user_client.on(events.NewMessage(chats=self.monitor_channels))
        async def handler(event: Any) -> None:
            await self.process_message(event)

        print("Monitoring started. Press Ctrl+C to stop.")
        await self.user_client.run_until_disconnected()

    async def main_async(self) -> None:
        self.setup_clients()
        assert self.user_client is not None
        await self.user_client.connect()

        if not await self.authorize_user():
            return

        await self.start_monitoring_async()

    def run(self) -> None:
        try:
            asyncio.run(self.main_async())
        except KeyboardInterrupt:
            print("Bot stopped by user.")


def main() -> None:
    settings = Settings.load()
    bot = SimpleOlympiadBot(settings)
    bot.run()


if __name__ == "__main__":
    main()
