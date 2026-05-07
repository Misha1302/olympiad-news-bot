# Security notes

Never commit real credentials or runtime sessions:

- Telegram `API_ID`, `API_HASH`, `BOT_TOKEN`;
- GigaChat authorization key;
- `.env` and `config.py` with secrets;
- Telethon `*.session` and `*.session-journal` files;
- cookies, browser profiles, debug screenshots and logs.

Use `.env.example` as a template and keep the real `.env` only on the machine where the bot runs.

If a token or session file was accidentally sent to a public repository, consider it compromised and rotate it immediately.
