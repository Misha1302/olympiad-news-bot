# Copy this file to SECRETS.py and fill in real values.
# Do not commit SECRETS.py.

TELEGRAM_API_ID = 123456
TELEGRAM_API_HASH = "replace_me"
TELEGRAM_BOT_TOKEN = "123456:replace_me"

IDS_TO_CHAT = ["123456789", "987654321"]
MONITOR_CHANNELS = [
    "@codeforces_official",
    "@olymp_itmo11",
    "@olymp_mephi",
]

GIGACHAT_ENABLED = True
GIGACHAT_AUTH_KEY = "replace_me"
GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
GIGACHAT_MODEL = "GigaChat"
GIGACHAT_VERIFY_SSL = True
GIGACHAT_TIMEOUT_SECONDS = 30
GIGACHAT_MAX_RETRIES = 3
GIGACHAT_FAIL_OPEN = True
GIGACHAT_MAX_TEXT_CHARS = 5000
GIGACHAT_CA_BUNDLE = None

# Each destination/message-part is retried independently, preventing duplicate
# resends of parts that were already delivered successfully.
TELEGRAM_SEND_MAX_RETRIES = 3

# Queue uses backpressure rather than silently dropping new messages.
MESSAGE_QUEUE_SIZE = 100
DELIVERY_RECEIPT_DB_PATH = ".runtime/delivery.sqlite3"
