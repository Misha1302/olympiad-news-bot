# Olympiad News Bot

Telegram-бот для мониторинга олимпиадных каналов. Бот читает новые сообщения через пользовательскую Telegram-сессию, выполняет быстрый локальный prefilter, при необходимости проверяет сообщение через GigaChat и отправляет подходящие новости в заданные чаты.

Браузер, Selenium, ChromeDriver и cookies не нужны.

## Требования

- Python **3.12**;
- `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` с `my.telegram.org`;
- `TELEGRAM_BOT_TOKEN` от `@BotFather`;
- `IDS_TO_CHAT` — id получателей;
- `GIGACHAT_AUTH_KEY`, если включена AI-фильтрация.

Поддерживаемый диапазон Python зафиксирован в `pyproject.toml`: `>=3.12,<3.13`.

## Быстрый запуск

Для первой установки:

```bash
bash setup_and_run.sh
```

Скрипт скачает или обновит репозиторий в `~/olympiad-news-bot`, проверит наличие Python 3.12, создаст `.venv`, установит пакет, предложит заполнить секреты и запустит бота.

Для повторного запуска:

```bash
cd ~/olympiad-news-bot
bash run.sh
```

При первом запуске Telegram может попросить номер телефона, код входа и пароль двухэтапной аутентификации.

## Ручная установка

```bash
git clone https://github.com/Misha1302/olympiad-news-bot.git
cd olympiad-news-bot
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip check
cp SECRETS.example.py SECRETS.py
nano SECRETS.py
python -m olympiad_news_bot.main
```

## Конфигурация

Основной локальный вариант — `SECRETS.py`, созданный из `SECRETS.example.py`. Переменные окружения и `.env` поддерживаются как fallback для CI и hosting-платформ.

Пример каналов:

```python
MONITOR_CHANNELS = [
    "@codeforces_official",
    "@olymp_itmo11",
    "@olymp_mephi",
]
```

Если список пуст, используются встроенные каналы по умолчанию.

Важные настройки надёжности:

```python
TELEGRAM_SEND_MAX_RETRIES = 3
MESSAGE_QUEUE_SIZE = 100
DELIVERY_RECEIPT_DB_PATH = ".runtime/delivery.sqlite3"
GIGACHAT_FAIL_OPEN = True
```

- отправка ретраится отдельно для каждого получателя и каждой части сообщения; успешные части записываются в SQLite receipt store и пропускаются при обычном повторе или рестарте;
- очередь использует backpressure и не отбрасывает новые сообщения молча;
- при завершении runtime дожидается обработки уже принятых сообщений;
- `GIGACHAT_FAIL_OPEN=True` разрешает отправку после успешного keyword-prefilter, если GigaChat временно недоступен; `False` блокирует такую отправку.

## Архитектура

```text
TelethonMessageSource
        ↓ IncomingMessage
MessageQueue / BotRuntime
        ↓
NewsProcessor
  ├─ MessagePrefilter
  ├─ MessageClassifier
  ├─ NotificationFormatter
  └─ NotificationSink
        ↓
Telegram Bot API
```

Основные границы:

- `domain.py` — сообщения, решения классификатора, результаты обработки и доставки;
- `ports.py` — небольшие capability-контракты application-слоя;
- `application.py` — высокоуровневая политика без зависимостей от Telethon, `requests` и Bot API;
- `adapters/` — GigaChat и Telethon;
- `delivery.py` — Telegram delivery adapter с независимыми ретраями;
- `adapters/sqlite_receipts.py` — durable best-effort защита от повторной отправки уже подтверждённых частей;
- `runtime.py` и `queueing.py` — lifecycle, backpressure, graceful drain и наблюдаемая статистика;
- `main.py` — composition root.

Архитектурный тест запрещает application-слою напрямую импортировать `telethon`, `telebot`, `requests` и `urllib3`.

## Проверки

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
```

CI дополнительно устанавливает проект на Python 3.12 и запускает `pip check`. `pyproject.toml` является единственным каноническим источником dependency metadata; `requirements.txt` только делегирует установку editable-пакету.

## Остановка

В терминале нажмите `Ctrl+C`. Runtime перестаёт принимать новые сообщения и дожидается обработки очереди.

Если случайно запущено несколько копий:

```bash
pkill -f olympiad_news_bot
rm -f .runtime/*.session-journal .runtime/*.session-wal .runtime/*.session-shm
```

## Ошибка SSL при обращении к GigaChat

Сначала оставьте безопасный режим:

```python
GIGACHAT_VERIFY_SSL = True
```

При необходимости создайте локальный bundle сертификатов:

```bash
source .venv/bin/activate
python scripts/install_gigachat_certs.py
```

Скрипт проверит PEM-структуру сертификатов, напечатает их SHA-256 и предложит значение `GIGACHAT_CA_BUNDLE`. Bundle передаётся только GigaChat-адаптеру и не меняет global trust процесса. Временный небезопасный вариант:

```python
GIGACHAT_VERIFY_SSL = False
```

Используйте его только для диагностики.

## Что нельзя коммитить

```text
SECRETS.py
.env
.runtime/
*.session
*.session-journal
*.sqlite
*.sqlite3
logs/
*.log
__pycache__/
.venv/
```

Если секрет или Telegram-сессия попали в публичный commit, считайте их скомпрометированными и замените.
