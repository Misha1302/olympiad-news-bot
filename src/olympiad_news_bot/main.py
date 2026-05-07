import asyncio
import html
import os
import pickle
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import telebot
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from telethon import TelegramClient, events
from telethon.errors import PhoneNumberInvalidError, SessionPasswordNeededError

load_dotenv()

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


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def read_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


@dataclass(frozen=True)
class Settings:
    telegram_api_id: int
    telegram_api_hash: str
    telegram_bot_token: str
    ids_to_chat: list[str]
    monitor_channels: list[str]
    deepseek_enabled: bool
    deepseek_headless: bool
    deepseek_cookies_file: Path
    deepseek_max_checks_before_restart: int

    @staticmethod
    def load() -> "Settings":
        channels_env = os.getenv("MONITOR_CHANNELS", "")
        ids_to_chat = parse_csv(read_required_env("IDS_TO_CHAT"))
        if not ids_to_chat:
            raise RuntimeError("IDS_TO_CHAT must contain at least one chat ID")

        return Settings(
            telegram_api_id=int(read_required_env("TELEGRAM_API_ID")),
            telegram_api_hash=read_required_env("TELEGRAM_API_HASH"),
            telegram_bot_token=read_required_env("TELEGRAM_BOT_TOKEN"),
            ids_to_chat=ids_to_chat,
            monitor_channels=parse_csv(channels_env) or DEFAULT_MONITOR_CHANNELS,
            deepseek_enabled=os.getenv("DEEPSEEK_ENABLED", "true").lower() in {"1", "true", "yes", "y"},
            deepseek_headless=os.getenv("DEEPSEEK_HEADLESS", "false").lower() in {"1", "true", "yes", "y"},
            deepseek_cookies_file=Path(os.getenv("DEEPSEEK_COOKIES_FILE", ".runtime/deepseek_cookies.pkl")),
            deepseek_max_checks_before_restart=int(os.getenv("DEEPSEEK_MAX_CHECKS_BEFORE_RESTART", "5")),
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


class DeepSeekChecker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.initialized = False
        self.last_reset_time = time.time()
        self.session_checks_count = 0
        self.processing_lock = threading.Lock()

    def save_cookies(self) -> bool:
        try:
            if not self.driver:
                return False

            self.settings.deepseek_cookies_file.parent.mkdir(parents=True, exist_ok=True)
            cookies = self.driver.get_cookies()
            with self.settings.deepseek_cookies_file.open("wb") as file:
                pickle.dump(cookies, file, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"Cookies saved: {len(cookies)}")
            return True
        except (InvalidSessionIdException, WebDriverException) as error:
            print(f"Cannot save cookies, browser session is not valid: {error}")
            return False
        except Exception as error:
            print(f"Cannot save cookies: {error}")
            return False

    def load_cookies(self) -> list[dict[str, Any]] | None:
        try:
            if not self.settings.deepseek_cookies_file.exists():
                return None

            with self.settings.deepseek_cookies_file.open("rb") as file:
                cookies = pickle.load(file)
            print(f"Cookies loaded: {len(cookies)}")
            return cookies
        except Exception as error:
            print(f"Cannot load cookies: {error}")
            return None

    def check_driver_alive(self) -> bool:
        try:
            if not self.driver:
                return False
            _ = self.driver.current_url
            return True
        except Exception:
            return False

    def login_manually_if_needed(self) -> bool:
        try:
            if not self.check_driver_alive() or not self.driver:
                return True

            page_source = self.driver.page_source.lower()
            login_indicators = [
                "sign in",
                "signin",
                "log in",
                "login",
                "войти",
                "авторизация",
                "войдите",
                "email",
                "password",
                "пароль",
            ]

            if any(indicator in page_source for indicator in login_indicators):
                return True

            return self.find_textarea() is None
        except Exception as error:
            print(f"Cannot detect login state: {error}")
            return True

    def wait_for_manual_login(self, timeout_seconds: int = 120) -> bool:
        print("Manual DeepSeek login is required in the opened browser window.")
        started_at = time.time()
        while time.time() - started_at < timeout_seconds:
            if not self.login_manually_if_needed():
                self.save_cookies()
                print("DeepSeek login detected.")
                return True
            time.sleep(3)
        print("DeepSeek login timeout.")
        return False

    def initialize_driver(self, retry_count: int = 3) -> bool:
        for attempt in range(1, retry_count + 1):
            try:
                print(f"Initializing browser, attempt {attempt}...")
                self.cleanup()

                options = Options()
                if self.settings.deepseek_headless:
                    options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--user-data-dir=.runtime/chrome_profile")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)

                self.driver = webdriver.Chrome(options=options)
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.driver.implicitly_wait(10)
                self.wait = WebDriverWait(self.driver, 15)

                self.driver.get("https://chat.deepseek.com/")
                time.sleep(3)

                cookies = self.load_cookies()
                if cookies:
                    self.driver.delete_all_cookies()
                    for cookie in cookies:
                        if "name" in cookie and "value" in cookie:
                            self.driver.add_cookie(cookie)
                    self.driver.refresh()
                    time.sleep(3)

                if self.login_manually_if_needed() and not self.wait_for_manual_login():
                    continue

                self.initialized = True
                self.session_checks_count = 0
                self.last_reset_time = time.time()
                self.save_cookies()
                return True
            except Exception as error:
                print(f"Browser initialization failed: {error}")
                time.sleep(2)

        return False

    def find_textarea(self) -> Any | None:
        if not self.driver:
            return None

        selectors = [
            "[data-testid='message-input']",
            "textarea",
            "div[contenteditable='true']",
            ".ProseMirror",
            "input[type='text']",
            "div[role='textbox']",
            ".chat-input",
            "#prompt-textarea",
        ]

        for selector in selectors:
            try:
                for element in self.driver.find_elements(By.CSS_SELECTOR, selector):
                    if element.is_displayed() and element.is_enabled():
                        return element
            except Exception:
                continue
        return None

    def reset_chat_session(self) -> bool:
        if not self.driver and not self.initialize_driver():
            return False

        try:
            self.save_cookies()
            self.driver.execute_script("window.location.href = 'https://chat.deepseek.com/';")
            time.sleep(3)
            if self.login_manually_if_needed():
                return self.wait_for_manual_login(timeout_seconds=60)
            return self.find_textarea() is not None
        except Exception as error:
            print(f"Cannot reset DeepSeek session: {error}")
            return False

    def safe_send_keys(self, element: Any, text: str) -> bool:
        cleaned_text = remove_non_bmp_chars(text)
        try:
            element.clear()
            time.sleep(0.3)
            for index in range(0, len(cleaned_text), 100):
                element.send_keys(cleaned_text[index:index + 100])
                time.sleep(0.05)
            element.send_keys("\n")
            return True
        except Exception as error:
            print(f"Normal input failed, trying JavaScript input: {error}")
            try:
                self.driver.execute_script(
                    """
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """,
                    element,
                    cleaned_text,
                )
                return True
            except Exception:
                return False

    def get_last_response(self) -> str | None:
        if not self.driver:
            return None

        time.sleep(2)
        try:
            markdown_elements = self.driver.find_elements(By.CLASS_NAME, "ds-markdown")
            if markdown_elements:
                text = markdown_elements[-1].text.strip()
                if text:
                    return text
        except Exception:
            pass

        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            for line in body_text.split("\n"):
                normalized = line.strip().lower()
                if normalized in {"да", "нет"}:
                    return normalized.upper()
        except Exception:
            pass

        return None

    def check_with_deepseek(self, text: str, retry_count: int = 3) -> bool:
        for attempt in range(1, retry_count + 1):
            try:
                if not self.initialized and not self.initialize_driver():
                    continue

                self.session_checks_count += 1
                if self.session_checks_count >= self.settings.deepseek_max_checks_before_restart:
                    self.cleanup()
                    if not self.initialize_driver():
                        continue

                cleaned_text = remove_non_bmp_chars(text[:5000].replace("\n", " ").replace("\r", ""))
                prompt = (
                    f'Проанализируй это сообщение: "{cleaned_text}". '
                    'Относится ли оно к новостям, анонсам или итогам олимпиад? '
                    'Ответь только "ДА" или "НЕТ".'
                )

                textarea = self.find_textarea()
                if textarea is None:
                    if not self.reset_chat_session():
                        continue
                    textarea = self.find_textarea()
                    if textarea is None:
                        continue

                if not self.safe_send_keys(textarea, prompt):
                    continue

                time.sleep(10)
                response = self.get_last_response()
                if not response:
                    continue

                response_lower = remove_non_bmp_chars(response).lower()
                if "да" in response_lower:
                    return True
                if "нет" in response_lower:
                    return False

                positive_words = ["олимп", "соревнован", "конкурс", "задач", "решен", "турнир", "чемпионат"]
                return any(word in response_lower for word in positive_words)
            except Exception as error:
                print(f"DeepSeek check failed on attempt {attempt}: {error}")
                time.sleep(2)

        return False

    def check_message(self, text: str) -> bool:
        with self.processing_lock:
            return self.check_with_deepseek(text)

    def cleanup(self) -> None:
        if self.driver:
            try:
                self.save_cookies()
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
                self.wait = None
                self.initialized = False


class SimpleOlympiadBot:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ids_to_chat = settings.ids_to_chat
        self.monitor_channels = settings.monitor_channels
        self.user_client: Optional[TelegramClient] = None
        self.bot: Optional[telebot.TeleBot] = None
        self.deepseek_checker = DeepSeekChecker(settings)
        self.check_count = 0
        self.message_queue = MessageQueue(max_queue_size=50)
        self.queue_worker_task: Optional[asyncio.Task[Any]] = None
        self.stats_print_task: Optional[asyncio.Task[Any]] = None
        self.is_running = True

    def setup_clients(self) -> None:
        self.user_client = TelegramClient(".runtime/user_session", self.settings.telegram_api_id, self.settings.telegram_api_hash)
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
        if not self.is_olympiad_related(text):
            return False

        if not self.settings.deepseek_enabled:
            return True

        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self.deepseek_checker.check_message, text)
        except Exception as error:
            print(f"DeepSeek failed, falling back to keyword filter: {error}")
            return True

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

    def send_notification_with_retry(self, text: str, channel_name: str, message_id: int, max_retries: int = 3) -> bool:
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
                        fallback_message = f"НОВОСТЬ ОБ ОЛИМПИАДЕ\n\n{text[:200]}...\n\nИсточник: {channel_name}"
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
            self.send_notification_with_retry(text, task.channel_name, task.message_id)

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
                    self.message_queue.stats["errors"] += 1
                    self.message_queue.queue.task_done()
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

        if self.settings.deepseek_enabled:
            loop = asyncio.get_event_loop()
            initialized = await loop.run_in_executor(None, self.deepseek_checker.initialize_driver)
            if not initialized:
                print("DeepSeek initialization failed. The bot will use keyword filtering only.")

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
            self.deepseek_checker.cleanup()
            print(f"Final stats: {self.message_queue.get_stats()}")


def main() -> None:
    settings = Settings.load()
    bot = SimpleOlympiadBot(settings)
    bot.run()


if __name__ == "__main__":
    main()
