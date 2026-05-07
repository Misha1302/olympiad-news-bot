# Olympiad News Bot

Telegram-бот, который следит за олимпиадными каналами, предварительно фильтрует сообщения по ключевым словам и отправляет подходящие новости в заданные чаты.

## Что входит в репозиторий

- `src/olympiad_news_bot/main.py` — основной код бота.
- `requirements.txt` — зависимости Python.
- `.env.example` — пример конфигурации без секретов.
- `.gitignore` — защита от случайного коммита токенов, сессий, cookies и runtime-файлов.
- `SECURITY.md` — правила по секретам.

## Что намеренно не входит

Не храните в GitHub:

- реальные `API_ID`, `API_HASH`, `BOT_TOKEN`;
- `.env`, `config.py` с секретами;
- `*.session`, `*.session-journal` от Telethon;
- `deepseek_cookies.pkl` и другие cookies;
- `*.pyc`, `__pycache__`, `chrome_profile`, debug screenshots.

## Быстрый запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python -m src.olympiad_news_bot.main
```

На Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env
python -m src.olympiad_news_bot.main
```

## Важное замечание по DeepSeek

Текущая интеграция с DeepSeek сделана через Selenium и веб-интерфейс. Это хрупкая часть системы: верстка сайта, авторизация, cookies и антибот-защита могут сломать проверку. Для рабочего продукта лучше заменить это на официальный API или локальную модель-классификатор.
