# Olympiad News Bot with GigaChat

Telegram-бот следит за олимпиадными каналами, быстро отсекает явно нерелевантные сообщения по ключевым словам, а затем уточняет решение через GigaChat API.

Бот не использует браузерную автоматизацию: Selenium, ChromeDriver, cookies и ручной вход в веб-интерфейс не нужны.

## Требования

- Python 3.12.

Проект зафиксирован на Python 3.12 через `.python-version`. Не создавайте виртуальное окружение на Python 3.13/3.14: текущая версия Telethon из зависимостей импортирует стандартный модуль `imghdr`, которого в новых версиях Python уже нет.

## Что входит в репозиторий

- `src/olympiad_news_bot/main.py` — основной код бота.
- `SECRETS.example.py` — шаблон локального файла с секретами.
- `requirements.txt` — зависимости Python.
- `.env.example` — fallback-конфигурация для CI/хостинга без секретов.
- `.gitignore` — защита от случайного коммита токенов, сессий и runtime-файлов.
- `SECURITY.md` — правила по секретам.
- `.github/workflows/python-check.yml` — минимальная проверка синтаксиса в CI.

## Что нельзя хранить в GitHub

Не коммитьте:

- реальные `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_BOT_TOKEN`;
- `GIGACHAT_AUTH_KEY`;
- локальный `SECRETS.py`;
- `.env` с реальными значениями;
- `*.session`, `*.session-journal` от Telethon;
- debug screenshots и runtime logs;
- `*.pyc`, `__pycache__`, `.runtime/`.

## Быстрый запуск на Linux/macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp SECRETS.example.py SECRETS.py
nano SECRETS.py
PYTHONPATH=src python -m olympiad_news_bot.main
```

Если `python3.12` не найден на Fedora, установите Python 3.12 через пакетный менеджер или `pyenv`, затем удалите старое `.venv` и создайте его заново.

## Быстрый запуск на Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy SECRETS.example.py SECRETS.py
notepad SECRETS.py
$env:PYTHONPATH="src"
python -m olympiad_news_bot.main
```

## Настройка `SECRETS.py`

Минимально нужны:

```python
TELEGRAM_API_ID = 123456
TELEGRAM_API_HASH = "..."
TELEGRAM_BOT_TOKEN = "..."
IDS_TO_CHAT = ["123456789"]
GIGACHAT_ENABLED = True
GIGACHAT_AUTH_KEY = "..."
```

`GIGACHAT_AUTH_KEY` — это authorization key для получения OAuth access token. Можно указать ключ без префикса `Basic`; код сам добавит `Basic `. Если ключ уже начинается с `Basic `, он будет использован как есть.

`SECRETS.py` можно положить в корень репозитория или в `src/olympiad_news_bot/SECRETS.py`. Переменные окружения и `.env` остаются fallback-вариантом для CI или хостинга.

## Важные настройки GigaChat

```python
GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
GIGACHAT_MODEL = "GigaChat"
GIGACHAT_VERIFY_SSL = True
GIGACHAT_TIMEOUT_SECONDS = 30
GIGACHAT_MAX_RETRIES = 3
GIGACHAT_FAIL_OPEN = True
GIGACHAT_MAX_TEXT_CHARS = 5000
```

`GIGACHAT_FAIL_OPEN = True` означает: если сообщение прошло фильтр ключевых слов, но GigaChat временно недоступен, бот всё равно отправит сообщение. Это снижает риск пропустить важную новость, но может дать больше шума. Если важнее не спамить, поставьте `False`.

`GIGACHAT_VERIFY_SSL = True` безопаснее. Если локальная система не доверяет сертификатам GigaChat и запросы падают на SSL verification, временно можно поставить `False`, но это хуже с точки зрения безопасности.

## Как работает фильтрация

1. Telegram-сообщение попадает в очередь.
2. Быстрый локальный фильтр ищет олимпиадные ключевые слова и платформы.
3. Если локальный фильтр прошёл, сообщение отправляется в GigaChat.
4. GigaChat обязан вернуть только `ДА` или `НЕТ`.
5. При `ДА` бот пересылает короткое уведомление в заданные чаты.

## Ошибка `ModuleNotFoundError: No module named 'imghdr'`

Эта ошибка означает, что виртуальное окружение создано на слишком новой версии Python. Удалите `.venv` и пересоздайте его на Python 3.12:

```bash
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
PYTHONPATH=src python -m olympiad_news_bot.main
```
