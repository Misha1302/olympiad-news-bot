# Security notes

Never commit real credentials or runtime sessions:

- Telegram `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_BOT_TOKEN`;
- GigaChat authorization key;
- local `SECRETS.py`;
- `.env` files with real values;
- Telethon `*.session` and `*.session-journal` files;
- debug screenshots and logs.

Use `SECRETS.example.py` as a template, copy it to `SECRETS.py`, and keep the real `SECRETS.py` only on the machine where the bot runs.

Environment variables and `.env` remain supported as a fallback for CI or hosting platforms, but real `.env` files must also stay outside Git.

If a token or session file was accidentally committed to a public repository, consider it compromised and rotate it immediately.
