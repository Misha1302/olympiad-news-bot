import asyncio
import html
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


def load_local_secrets() -> dict[str, Any]:
    """
    Load local secrets from SECRETS.py without forcing that file into Git.

    Supported locations:
    - SECRETS.py in the repository root;
    - src/olympiad_news_bot/SECRETS.py for package-local deployments.

    Environment variables remain as a fallback for CI and hosting platforms.
    """

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


class ConfigurationError(RuntimeError):
    pass


def stringify_config_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (list, tuple, set)):
        return ",".join(
            item
            for item in (str(raw_item).strip() for raw_item in value)
            if item
        )

    return str(value).strip()


def read_config(name: str, default: Any = "") -> str:
    if name in LOCAL_SECRETS:
        return stringify_config_value(LOCAL_SECRETS[name])

    return stringify_config_value(os.getenv(name, default))


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def read_required_config(name: str) -> str:
    value = read_config(name)
    if not value:
        raise ConfigurationError(f"Configuration value {name} is required")
    return value


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
        channels_config = read_config("MONITOR_CHANNELS")
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
            monitor_channels=parse_csv(channels_config) or DEFAULT_MONITOR_CHANNELS,
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


@dataclass
class MessageTask:
    text: str
    channel_name: str
    message_id: int
    event: Any
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now()


class MessageQueue:
    def __init__(self, max_queue_size: int = 100) -> None:
        self.queue: asyncio.Queue[MessageTask] = asyncio.Queue(maxsize=max_queue_size)
        self.stats = {
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "queue_size": 0,
        }

    async def put(self, task: MessageTask) -> bool:
        try:
            self.queue.put_nowait(task)
            self.stats["queue_size"] = self.queue.qsize()
            print(f"Message added to queue. Queue size: {self.stats['queue_size']}")
            return True
        except asyncio.QueueFull:
            self.stats["skipped"] += 1
            print(f"Queue is full, message skipped: {task.text[:80]}")
            return False

    async def get(self) -> MessageTask:
        task = await self.queue.get()
        self.stats["queue_size"] = self.queue.qsize()
        return task

    def task_done(self) -> None:
        self.queue.task_done()
        self.stats["processed"] += 1
        self.stats["queue_size"] = self.queue.qsize()

    def task_failed(self) -> None:
        self.queue.task_done()
        self.stats["errors"] += 1
        self.stats["queue_size"] = self.queue.qsize()

    def get_stats(self) -> dict[str, int]:
        return {
            **self.stats,
            "current_queue_size": self.queue.qsize(),
        }


def remove_non_bmp_chars(text: str) -> str:
    if not text:
        return text

    text = re.sub(r"[\U00010000-\U0010FFFF]", "", text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text).strip()


def clean_text_for_telegram(text: str) -> str:
    if not text:
        return text

    safe_chars = re.compile(
        r"[^\w\s\d\.,!?\:;\-\(\)\[\]\{\}«»\"'\n\r\t\u0400-\u04FF\u0500-\u052F\u2DE0-\u2DFF\uA640-\uA69F]",
        re.UNICODE,
    )
    text = safe_chars.sub("", text)
    text = re.sub(r"\s+", " ", text)
    text = html.escape(text)

    for char in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(char, f"\\{char}")

    return text.strip()


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
            return self._check_message_with_retries(text)

    def _check_message_with_retries(self, text: str) -> bool:
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
        cleaned_text = remove_non_bmp_chars(text)
        cleaned_text = cleaned_text.replace("\n", " ").replace("\r", " ")
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()
        cleaned_text = cleaned_text[: self.settings.gigachat_max_text_chars]

        prompt = (
            "Ты строгий бинарный классификатор Telegram-сообщений для новостного бота.\n"
            "Цель бота — отправлять ТОЛЬКО сообщения про олимпиады школьников по информатике "
            "и программированию из перечня РСОШ или явно связанные с поступлением через такие олимпиады.\n\n"

            "Ответь ДА, только если сообщение содержит реальную полезную новость хотя бы одного из типов:\n"
            "1. регистрация на олимпиаду школьников по информатике/программированию;\n"
            "2. старт, дедлайн, перенос сроков или расписание этапа такой олимпиады;\n"
            "3. отборочный, заключительный, финальный этап олимпиады школьников по информатике/программированию;\n"
            "4. публикация результатов, проходных баллов, списков победителей/призёров;\n"
            "5. апелляции, дипломы, подтверждение участия, льготы БВИ/100 баллов по информатике;\n"
            "6. официальная новость конкретной олимпиады из перечня РСОШ по профилю информатика/программирование.\n\n"

            "Типичные релевантные олимпиады и маркеры: Высшая проба по информатике, Технокубок, "
            "олимпиада ИТМО/олимпиада школьников по информатике, Московская олимпиада школьников по информатике, "
            "СПбГУ по программированию/информатике, Иннополис, Когнитивные технологии, Росатом по информатике, "
            "Всесибирская по информатике, Открытая олимпиада школьников по программированию, "
            "профиль информатика, профиль программирование, РСОШ, БВИ, 100 баллов.\n\n"

            "Ответь НЕТ, если сообщение:\n"
            "1. про обычный спорт, матч, чемпионат, турнир или спортивное мероприятие;\n"
            "2. про Codeforces/ICPC/ACM/контест, если нет связи с олимпиадой школьников, РСОШ, БВИ или поступлением;\n"
            "3. про математику, физику, инженерный конкурс или вузовское мероприятие без информатики/программирования;\n"
            "4. про студенческие, корпоративные, взрослые или коммерческие соревнования без школьной РСОШ-связи;\n"
            "5. является техническим тестом, проверкой фильтра, фразой вроде 'не должно пройти', "
            "'тестовое сообщение', 'проверка', 'ignore this';\n"
            "6. просто содержит слова 'результаты', 'олимпиада', 'турнир', 'соревнование', но не говорит явно "
            "о школьной олимпиаде по информатике/программированию.\n\n"

            "Если сомневаешься, ответь НЕТ.\n"
            "Ответ должен быть строго одним словом: ДА или НЕТ.\n\n"
            f"Сообщение: {cleaned_text}"
        )

        payload = {
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
                    "content": prompt,
                },
            ],
            "temperature": 0,
            "max_tokens": 8,
        }

        response = requests.post(
            self.CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {self._get_access_token()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=self.settings.gigachat_timeout_seconds,
            verify=self.settings.gigachat_verify_ssl,
        )

        if response.status_code == 401:
            self._drop_access_token()
            response = requests.post(
                self.CHAT_COMPLETIONS_URL,
                headers={
                    "Authorization": f"Bearer {self._get_access_token(force_refresh=True)}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=self.settings.gigachat_timeout_seconds,
                verify=self.settings.gigachat_verify_ssl,
            )

        response.raise_for_status()
        content = self._extract_answer(response.json())
        return self._parse_answer(content)

    def _get_access_token(self, force_refresh: bool = False) -> str:
        now_ms = int(time.time() * 1000)
        if (
            not force_refresh
            and self._access_token
            and self._access_token_expires_at_ms > now_ms + 60_000
        ):
            return self._access_token

        auth_header = self._build_auth_header()
        response = requests.post(
            self.OAUTH_URL,
            headers={
                "Authorization": auth_header,
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
        access_token = str(data.get("access_token", "")).strip()
        if not access_token:
            raise RuntimeError("GigaChat OAuth response does not contain access_token")

        expires_at = data.get("expires_at")
        if expires_at is None:
            expires_at_ms = int((time.time() + 25 * 60) * 1000)
        else:
            expires_at_ms = int(expires_at)

        self._access_token = access_token
        self._access_token_expires_at_ms = expires_at_ms
        return access_token

    def _drop_access_token(self) -> None:
        self._access_token = None
        self._access_token_expires_at_ms = 0

    def _build_auth_header(self) -> str:
        if not self.settings.gigachat_auth_key:
            raise ConfigurationError("GIGACHAT_AUTH_KEY is required")

        auth_key = self.settings.gigachat_auth_key.strip()
        if auth_key.lower().startswith("basic "):
            return auth_key
        return f"Basic {auth_key}"

    @staticmethod
    def _extract_answer(response_json: dict[str, Any]) -> str:
        try:
            return str(response_json["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected GigaChat response shape: {response_json}") from error

    @staticmethod
    def _parse_answer(answer: str) -> bool:
        normalized = answer.strip().lower()
        normalized = normalized.replace(".", "").replace("!", "").replace("\"", "")
        normalized = normalized.replace("'", "")

        if normalized.startswith("да") or normalized.startswith("yes"):
            return True
        if normalized.startswith("нет") or normalized.startswith("no"):
            return False

        positive_words = ["олимп", "соревнован", "конкурс", "задач", "турнир", "чемпионат"]
        negative_words = ["не относится", "не связано", "нет"]
        if any(word in normalized for word in negative_words):
            return False
        if any(word in normalized for word in positive_words):
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
        self.message_queue = MessageQueue(max_queue_size=50)
        self.queue_worker_task: asyncio.Task[Any] | None = None
        self.stats_print_task: asyncio.Task[Any] | None = None
        self.is_running = True

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
        if not text or len(text) < 10:
            return False

        text_lower = remove_non_bmp_chars(text).lower()
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

    def format_message(self, text: str, channel_name: str, message_id: int) -> str:
        text = clean_text_for_telegram(text)
        if len(text) > 300:
            text = text[:300] + "..."

        if channel_name.startswith("@"):
            channel_link = f"https://t.me/{channel_name[1:]}/{message_id}"
            source_text = f"[{channel_name}]({channel_link})"
        else:
            source_text = f"Канал: {clean_text_for_telegram(channel_name)}"

        return f"""
*НОВОСТЬ ОБ ОЛИМПИАДЕ*

{text}

*Источник:* {source_text}
*Время:* {datetime.now().strftime('%H:%M %d.%m.%Y')}

#олимпиада #программирование
""".strip()

    def send_notification_with_retry(
        self,
        text: str,
        channel_name: str,
        message_id: int,
        max_retries: int = 3,
    ) -> bool:
        assert self.bot is not None
        for attempt in range(max_retries):
            try:
                formatted_message = self.format_message(text, channel_name, message_id)
                for chat_id in self.ids_to_chat:
                    try:
                        self.bot.send_message(
                            chat_id,
                            formatted_message,
                            parse_mode="Markdown",
                            disable_web_page_preview=True,
                        )
                    except Exception as error:
                        print(f"Cannot send formatted message to {chat_id}: {error}")
                        fallback_message = (
                            f"НОВОСТЬ ОБ ОЛИМПИАДЕ\n\n{text[:200]}...\n\nИсточник: {channel_name}"
                        )
                        self.bot.send_message(chat_id, fallback_message)
                return True
            except Exception as error:
                wait_time = 2 ** attempt
                print(f"Notification send failed, attempt {attempt + 1}: {error}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
        return False

    async def process_message_task(self, task: MessageTask) -> None:
        text = task.event.message.text or task.event.message.message
        if not text or not text.strip():
            return

        if await self.should_send_message(text):
            print(f"Sending olympiad news from {task.channel_name}: {text[:80]}")
            self.send_notification_with_retry(text, task.channel_name, task.message_id)
        else:
            print(f"Message skipped: {text[:80]}")

    async def handle_new_message(self, event: Any) -> None:
        text = event.message.text or event.message.message
        if not text or not text.strip():
            return

        chat = await event.get_chat()
        if getattr(chat, "username", None):
            channel_name = f"@{chat.username}"
        elif getattr(chat, "title", None):
            channel_name = chat.title
        else:
            channel_name = f"ID: {chat.id}"

        task = MessageTask(
            text=text,
            channel_name=channel_name,
            message_id=event.message.id,
            event=event,
        )
        await self.message_queue.put(task)

    async def queue_worker(self) -> None:
        print("Queue worker started.")
        while self.is_running:
            try:
                task = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                try:
                    await self.process_message_task(task)
                    self.message_queue.task_done()
                except Exception as error:
                    self.message_queue.task_failed()
                    print(f"Task processing failed: {error}")
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as error:
                print(f"Queue worker failed: {error}")
                await asyncio.sleep(1)

    async def print_queue_stats(self) -> None:
        while self.is_running:
            try:
                stats = self.message_queue.get_stats()
                if stats["processed"] or stats["queue_size"] or stats["errors"]:
                    print(f"Queue stats: {stats}")
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break

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
            await self.handle_new_message(event)

        print("Monitoring started. Press Ctrl+C to stop.")
        await self.user_client.run_until_disconnected()

    async def main_async(self) -> None:
        self.setup_clients()
        assert self.user_client is not None
        await self.user_client.connect()

        if not await self.authorize_user():
            return

        self.queue_worker_task = asyncio.create_task(self.queue_worker())
        self.stats_print_task = asyncio.create_task(self.print_queue_stats())
        await self.start_monitoring_async()

    def run(self) -> None:
        try:
            asyncio.run(self.main_async())
        except KeyboardInterrupt:
            print("Bot stopped by user.")
        finally:
            self.is_running = False
            if self.queue_worker_task:
                self.queue_worker_task.cancel()
            if self.stats_print_task:
                self.stats_print_task.cancel()
            print(f"Final stats: {self.message_queue.get_stats()}")


def main() -> None:
    settings = Settings.load()
    bot = SimpleOlympiadBot(settings)
    bot.run()


if __name__ == "__main__":
    main()
