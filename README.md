# Olympiad News Bot

Простой Telegram-бот для мониторинга олимпиадных каналов.

Бот читает сообщения из заданных Telegram-каналов, проверяет их по ключевым словам и через GigaChat, а затем отправляет подходящие новости в нужный чат.

Браузер, Selenium, ChromeDriver и cookies не нужны.

## 1. Что нужно заранее

Перед запуском подготовьте:

1. **Python 3.12**.
2. `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` — взять на https://my.telegram.org.
3. `TELEGRAM_BOT_TOKEN` — создать бота через `@BotFather`.
4. `IDS_TO_CHAT` — id чата или пользователя, куда бот будет отправлять новости.
5. `GIGACHAT_AUTH_KEY` — ключ авторизации GigaChat API.

Важно: используйте именно **Python 3.12**. На Python 3.13/3.14 бот может упасть из-за зависимости Telethon от модуля `imghdr`.

## 2. Установка проекта

Склонируйте репозиторий:

```bash
git clone https://github.com/Misha1302/olympiad-news-bot.git
cd olympiad-news-bot
```

Создайте виртуальное окружение и установите зависимости:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Если команда `python3.12` не найдена, сначала установите Python 3.12 для своей системы.

## 3. Настройка секретов

Скопируйте пример файла секретов:

```bash
cp SECRETS.example.py SECRETS.py
```

Откройте файл:

```bash
nano SECRETS.py
```

Заполните реальные значения:

```python
TELEGRAM_API_ID = 123456
TELEGRAM_API_HASH = "your_api_hash"
TELEGRAM_BOT_TOKEN = "your_bot_token"

IDS_TO_CHAT = ["123456789"]

GIGACHAT_ENABLED = True
GIGACHAT_AUTH_KEY = "your_gigachat_auth_key"
```

`SECRETS.py` — локальный файл. Его нельзя коммитить в GitHub.

Если GigaChat пока не нужен, можно временно отключить его:

```python
GIGACHAT_ENABLED = False
GIGACHAT_AUTH_KEY = ""
```

Тогда бот будет использовать только локальный фильтр по ключевым словам.

## 4. Запуск

Запустите бота из корня репозитория:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m olympiad_news_bot.main
```

При первом запуске Telethon может попросить:

1. номер телефона Telegram;
2. код входа из Telegram;
3. пароль двухэтапной аутентификации, если он включён.

После успешного входа рядом появится локальная Telegram-сессия. Повторно входить обычно не нужно.

## 5. Как поменять каналы

Каналы можно указать в `SECRETS.py`:

```python
MONITOR_CHANNELS = [
    "@codeforces_official",
    "@olymp_itmo11",
    "@olymp_mephi",
]
```

Если `MONITOR_CHANNELS` пустой или не указан, бот использует список каналов по умолчанию из кода.

## 6. Как остановить бота

В терминале нажмите:

```text
Ctrl+C
```

Если бот завис или был случайно запущен несколько раз:

```bash
pkill -f olympiad_news_bot
```

## 7. Частые ошибки

### `ModuleNotFoundError: No module named 'imghdr'`

Скорее всего виртуальное окружение создано на Python 3.13 или новее.

Исправление:

```bash
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### `sqlite3.OperationalError: database is locked`

Обычно это значит, что уже запущена другая копия бота с той же Telegram-сессией.

Исправление:

```bash
pkill -f olympiad_news_bot
rm -f .runtime/*.session-journal .runtime/*.session-wal .runtime/*.session-shm
```

После этого запустите бота снова.

### Ошибка SSL при обращении к GigaChat

Сначала попробуйте оставить безопасный вариант:

```python
GIGACHAT_VERIFY_SSL = True
```

Если система не доверяет сертификатам GigaChat, можно создать локальный bundle сертификатов:

```bash
source .venv/bin/activate
python scripts/install_gigachat_certs.py
```

Скрипт напечатает команду `export REQUESTS_CA_BUNDLE=...`. Выполните её перед запуском бота.

Временный небезопасный вариант:

```python
GIGACHAT_VERIFY_SSL = False
```

Используйте его только если нужно срочно проверить запуск.

## 8. Какие файлы нельзя выкладывать в GitHub

Не коммитьте:

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

Эти файлы уже добавлены в `.gitignore`, но всё равно проверяйте перед коммитом.

## 9. Короткая памятка запуска

```bash
git clone https://github.com/Misha1302/olympiad-news-bot.git
cd olympiad-news-bot
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp SECRETS.example.py SECRETS.py
nano SECRETS.py
PYTHONPATH=src python -m olympiad_news_bot.main
```
