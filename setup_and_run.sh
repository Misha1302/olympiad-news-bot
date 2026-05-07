#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Misha1302/olympiad-news-bot.git"
PROJECT_DIR="$HOME/olympiad-news-bot"
PYTHON_BIN="python3"

echo "== Olympiad News Bot setup =="

install_system_dependencies() {
    if command -v apt-get >/dev/null 2>&1; then
        echo "Detected Ubuntu/Debian"
        sudo apt-get update
        sudo apt-get install -y git python3 python3-venv python3-pip ca-certificates
    elif command -v dnf >/dev/null 2>&1; then
        echo "Detected Fedora"
        sudo dnf install -y git python3 python3-pip ca-certificates
    elif command -v pacman >/dev/null 2>&1; then
        echo "Detected Arch"
        sudo pacman -S --needed --noconfirm git python python-pip ca-certificates
        PYTHON_BIN="python"
    else
        echo "Unsupported Linux distribution."
        echo "Install manually: git, python3, python3-venv, python3-pip"
        exit 1
    fi
}

clone_or_update_repo() {
    if [ -d "$PROJECT_DIR/.git" ]; then
        echo "Repository already exists. Updating main branch..."
        cd "$PROJECT_DIR"
        git fetch origin
        git checkout main
        git pull origin main
    else
        echo "Cloning repository..."
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
        git checkout main
    fi
}

create_virtualenv() {
    cd "$PROJECT_DIR"

    if [ ! -d ".venv" ]; then
        echo "Creating Python virtual environment..."
        "$PYTHON_BIN" -m venv .venv
    fi

    source .venv/bin/activate

    echo "Installing Python dependencies..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

    mkdir -p .runtime
}

create_secrets_if_missing() {
    cd "$PROJECT_DIR"

    if [ -f "SECRETS.py" ]; then
        echo "SECRETS.py already exists. Keeping it unchanged."
        return
    fi

    echo
    echo "Now enter bot secrets."
    echo "You can get TELEGRAM_API_ID and TELEGRAM_API_HASH here: https://my.telegram.org"
    echo "You can get TELEGRAM_BOT_TOKEN from @BotFather"
    echo

    read -r -p "TELEGRAM_API_ID: " TELEGRAM_API_ID
    read -r -p "TELEGRAM_API_HASH: " TELEGRAM_API_HASH
    read -r -p "TELEGRAM_BOT_TOKEN: " TELEGRAM_BOT_TOKEN
    read -r -p "IDS_TO_CHAT, comma-separated, example 123456789,-1001234567890: " IDS_TO_CHAT

    echo
    read -r -p "MONITOR_CHANNELS, comma-separated, empty = default channels: " MONITOR_CHANNELS

    echo
    read -r -p "Use GigaChat filtering? y/n [y]: " USE_GIGACHAT
    USE_GIGACHAT="${USE_GIGACHAT:-y}"

    if [[ "$USE_GIGACHAT" =~ ^[YyДд]$ ]]; then
        GIGACHAT_ENABLED="true"
        read -r -p "GIGACHAT_AUTH_KEY: " GIGACHAT_AUTH_KEY
    else
        GIGACHAT_ENABLED="false"
        GIGACHAT_AUTH_KEY=""
    fi

    export TELEGRAM_API_ID
    export TELEGRAM_API_HASH
    export TELEGRAM_BOT_TOKEN
    export IDS_TO_CHAT
    export MONITOR_CHANNELS
    export GIGACHAT_ENABLED
    export GIGACHAT_AUTH_KEY

    python - <<'PY'
import json
import os

def py_string(name: str) -> str:
    return json.dumps(os.environ.get(name, ""), ensure_ascii=False)

content = f'''# Local secrets for olympiad-news-bot.
# Do not commit this file to Git.

TELEGRAM_API_ID = int({py_string("TELEGRAM_API_ID")})
TELEGRAM_API_HASH = {py_string("TELEGRAM_API_HASH")}
TELEGRAM_BOT_TOKEN = {py_string("TELEGRAM_BOT_TOKEN")}

IDS_TO_CHAT = {py_string("IDS_TO_CHAT")}

# Empty string means: use default channels from the code.
MONITOR_CHANNELS = {py_string("MONITOR_CHANNELS")}

GIGACHAT_ENABLED = {py_string("GIGACHAT_ENABLED")}
GIGACHAT_AUTH_KEY = {py_string("GIGACHAT_AUTH_KEY")}

GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
GIGACHAT_MODEL = "GigaChat"
GIGACHAT_VERIFY_SSL = True
GIGACHAT_TIMEOUT_SECONDS = 30
GIGACHAT_MAX_RETRIES = 3
GIGACHAT_FAIL_OPEN = True
GIGACHAT_MAX_TEXT_CHARS = 5000
'''

with open("SECRETS.py", "w", encoding="utf-8") as file:
    file.write(content)
PY

    chmod 600 SECRETS.py
    echo "Created SECRETS.py"
}

run_bot() {
    cd "$PROJECT_DIR"
    source .venv/bin/activate

    echo
    echo "Starting bot..."
    echo "On first run, Telegram may ask for phone number and login code."
    echo

    PYTHONPATH="$PROJECT_DIR/src" python -m olympiad_news_bot.main
}

install_system_dependencies
clone_or_update_repo
create_virtualenv
create_secrets_if_missing
run_bot
