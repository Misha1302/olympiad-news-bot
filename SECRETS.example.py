# Copy this file to SECRETS.py and fill in real values.
# Do not commit SECRETS.py.

# Telegram application credentials from https://my.telegram.org
TELEGRAM_API_ID = 123456
TELEGRAM_API_HASH = "replace_me"

# Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN = "123456:replace_me"

# Chat IDs that should receive notifications.
# A comma-separated string and a list[str] are both supported.
IDS_TO_CHAT = ["123456789", "987654321"]

# Optional Telegram channels to monitor.
# Leave the variable absent or empty to use the built-in defaults.
MONITOR_CHANNELS = [
    "@codeforces_official",
    "@olymp_itmo11",
    "@olymp_mephi",
]

GIGACHAT_ENABLED = True

# GigaChat authorization key for OAuth token request.
# The code accepts both raw Base64 value and a value prefixed with "Basic ".
GIGACHAT_AUTH_KEY = "replace_me"

GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
GIGACHAT_MODEL = "GigaChat"
GIGACHAT_VERIFY_SSL = True
GIGACHAT_TIMEOUT_SECONDS = 30
GIGACHAT_MAX_RETRIES = 3
GIGACHAT_FAIL_OPEN = True
GIGACHAT_MAX_TEXT_CHARS = 5000
