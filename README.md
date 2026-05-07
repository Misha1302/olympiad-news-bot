# Olympiad News Bot

Простой Telegram-бот для мониторинга олимпиадных каналов.

Бот читает сообщения из заданных Telegram-каналов, проверяет их по ключевым словам и через GigaChat, а затем отправляет подходящие новости в нужный чат.

Браузер, Selenium, ChromeDriver и cookies не нужны.

## Самый простой запуск

Для первого запуска используйте готовый скрипт:

```bash
bash setup_and_run.sh
```

Скрипт сам:

1. определит Ubuntu/Debian, Fedora или Arch;
2. установит системные зависимости;
3. скачает или обновит репозиторий в `~/olympiad-news-bot`;
4. создаст виртуальное окружение `.venv`;
5. установит зависимости из `requirements.txt`;
6. спросит секреты;
7. создаст локальный `SECRETS.py`;
8. запустит бота.

При первом запуске Telegram может попросить номер телефона, код входа и пароль двухэтапной аутентификации.

## Повторный запуск

Если проект уже установлен, зайдите в папку проекта и используйте короткий скрипт:

```bash
cd ~/olympiad-news-bot
bash run.sh
```

`run.sh` проверит `SECRETS.py`, создаст `.venv`, если его нет, установит зависимости и запустит бота.

## Что нужно подготовить заранее

Перед запуском желательно иметь:

1. `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` — взять на https://my.telegram.org.
2. `TELEGRAM_BOT_TOKEN` — создать бота через `@BotFather`.
3. `IDS_TO_CHAT` — id чата или пользователя, куда бот будет отправлять новости.
4. `GIGACHAT_AUTH_KEY` — ключ авторизации GigaChat API.

Если GigaChat пока не нужен, при вопросе `Use GigaChat filtering?` ответьте `n`.

## Как остановить бота

В терминале нажмите:

```text
Ctrl+C
```

Если бот завис или был случайно запущен несколько раз:

```bash
pkill -f olympiad_news_bot
```

## Как поменять настройки

Основные настройки лежат в локальном файле:

```text
SECRETS.py
```

Его можно открыть и изменить:

```bash
nano SECRETS.py
```

Например, каналы можно указать так:

```python
MONITOR_CHANNELS = [
    "@codeforces_official",
    "@olymp_itmo11",
    "@olymp_mephi",
]
```

Если `MONITOR_CHANNELS` пустой, бот использует список каналов по умолчанию из кода.

## Частые ошибки

### `sqlite3.OperationalError: database is locked`

Обычно это значит, что уже запущена другая копия бота с той же Telegram-сессией.

Исправление:

```bash
pkill -f olympiad_news_bot
rm -f .runtime/*.session-journal .runtime/*.session-wal .runtime/*.session-shm
```

После этого запустите бота снова:

```bash
bash run.sh
```

### `ModuleNotFoundError: No module named 'imghdr'`

Скорее всего виртуальное окружение создано на слишком новой версии Python.

Проект рассчитан на Python 3.12. Удалите старое окружение и запустите скрипт снова:

```bash
rm -rf .venv
bash run.sh
```

### Ошибка SSL при обращении к GigaChat

Сначала попробуйте безопасный вариант:

```python
GIGACHAT_VERIFY_SSL = True
```

Если система не доверяет сертификатам GigaChat, можно создать локальный bundle сертификатов:

```bash
source .venv/bin/activate
python scripts/install_gigachat_certs.py
```

Скрипт напечатает команду `export REQUESTS_CA_BUNDLE=...`. Выполните её перед запуском бота.

Временный небезопасный вариант в `SECRETS.py`:

```python
GIGACHAT_VERIFY_SSL = False
```

Используйте его только если нужно срочно проверить запуск.

## Какие файлы нельзя выкладывать в GitHub

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

## Для ручного запуска без скриптов

Обычно это не нужно. Используйте `setup_and_run.sh` для первого запуска и `run.sh` для повторных запусков.

Ручной вариант нужен только для отладки:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp SECRETS.example.py SECRETS.py
nano SECRETS.py
PYTHONPATH=src python -m olympiad_news_bot.main
```
