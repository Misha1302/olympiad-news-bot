# Security policy

## Never commit

- Telegram bot tokens.
- Telegram API ID/API hash.
- Telethon session files: `*.session`, `*.session-journal`.
- Browser cookies: `*.pkl`, especially `deepseek_cookies.pkl`.
- Local `.env` and `config.py` files with real values.
- Compiled Python files: `*.pyc`, because they can still contain recoverable constants.

## If a secret was committed or shared

1. Revoke the Telegram bot token in @BotFather and create a new one.
2. Recreate or rotate Telegram API credentials where possible.
3. Terminate unknown Telegram sessions in Telegram settings.
4. Delete DeepSeek cookies and sign in again.
5. Rewrite public Git history if the secret reached GitHub.
