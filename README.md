# Olympiad News Bot with GigaChat

Telegram-бот следит за олимпиадными каналами, быстро отсекает явно нерелевантные сообщения по ключевым словам, а затем уточняет решение через GigaChat API.

В этой версии удалена хрупкая Selenium-интеграция с DeepSeek. Браузер, cookies и ручной вход больше не нужны.

## Что входит в репозиторий

- `src/olympiad_news_bot/main.py` — основной код бота.
- `requirements.txt` — зависимости Python.
- `.env.example` — пример конфигурации без секретов.
- `.gitignore` — защита от случайного коммита токенов, сессий, cookies и runtime-файлов.
- `SECURITY.md` — правила по секретам.
- `.github/workflows/python-check.yml` — минимальная проверка синтаксиса в CI.

## Что нельзя хранить в GitHub

Не коммитьте:

- реальные `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_BOT_TOKEN`;
- `GIGACHAT_AUTH_KEY`;
- `.env`, `config.py` с секретами;
- `*.session`, `*.session-journal` от Telethon;
- cookies, `.pkl`, browser profile, debug screenshots;
- `*.pyc`, `__pycache__`, `.runtime/`.

## Быстрый запуск на Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
PYTHONPATH=src python -m olympiad_news_bot.main
```

## Быстрый запуск на Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env
$env:PYTHONPATH="src"
python -m olympiad_news_bot.main
```

## Настройка `.env`

Минимально нужны:

```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=...
TELEGRAM_BOT_TOKEN=...
IDS_TO_CHAT=123456789
GIGACHAT_ENABLED=true
GIGACHAT_AUTH_KEY=...
```

`GIGACHAT_AUTH_KEY` — это authorization key для получения OAuth access token. Можно указать ключ без префикса `Basic`; код сам добавит `Basic `. Если ключ уже начинается с `Basic `, он будет использован как есть.

## Важные настройки GigaChat

```env
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_MODEL=GigaChat
GIGACHAT_VERIFY_SSL=true
GIGACHAT_TIMEOUT_SECONDS=30
GIGACHAT_MAX_RETRIES=3
GIGACHAT_FAIL_OPEN=true
GIGACHAT_MAX_TEXT_CHARS=5000
```

`GIGACHAT_FAIL_OPEN=true` означает: если сообщение прошло фильтр ключевых слов, но GigaChat временно недоступен, бот всё равно отправит сообщение. Это снижает риск пропустить важную новость, но может дать больше шума. Если важнее не спамить, поставьте `false`.

`GIGACHAT_VERIFY_SSL=true` безопаснее. Если локальная система не доверяет сертификатам GigaChat и запросы падают на SSL verification, временно можно поставить `false`, но это хуже с точки зрения безопасности.

## Как работает фильтрация

1. Telegram-сообщение попадает в очередь.
2. Быстрый локальный фильтр ищет олимпиадные ключевые слова и платформы.
3. Если локальный фильтр прошёл, сообщение отправляется в GigaChat.
4. GigaChat обязан вернуть только `ДА` или `НЕТ`.
5. При `ДА` бот пересылает короткое уведомление в заданные чаты.

## Что изменено относительно DeepSeek-версии

- Удалены Selenium, ChromeDriver, cookies и ручная авторизация в веб-интерфейсе.
- Добавлен `GigaChatClassifier` с OAuth-токеном, кешированием access token и повтором при `401`.
- Секреты читаются только из `.env` / переменных окружения.
- Runtime-сессии Telethon лежат в `.runtime/`, который исключён из Git.
- Добавлен режим `GIGACHAT_FAIL_OPEN` для осознанного поведения при сбоях LLM.
