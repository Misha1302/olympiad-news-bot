#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Misha1302/olympiad-news-bot.git"
PROJECT_DIR="$HOME/olympiad-news-bot"

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
    else
        echo "Unsupported Linux distribution."
        echo "Install Git, Python 3.12, venv, pip and CA certificates manually."
        exit 1
    fi
}

resolve_python_312() {
    if command -v python3.12 >/dev/null 2>&1; then
        printf '%s\n' "python3.12"
        return
    fi

    if command -v python3 >/dev/null 2>&1 \
        && [ "$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" = "3.12" ]; then
        printf '%s\n' "python3"
        return
    fi

    echo "Python 3.12 is required, but the package manager did not provide it." >&2
    echo "Install Python 3.12 for your distribution and run setup_and_run.sh again." >&2
    exit 1
}

clone_or_update_repo() {
    if [ -d "$PROJECT_DIR/.git" ]; then
        echo "Repository already exists. Updating main branch..."
        cd "$PROJECT_DIR"
        git fetch origin
        git checkout main
        git pull --ff-only origin main
    else
        echo "Cloning repository..."
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
        git checkout main
    fi
}

create_virtualenv() {
    cd "$PROJECT_DIR"
    local python_bin
    python_bin="$(resolve_python_312)"

    if [ -x ".venv/bin/python" ]; then
        local venv_version
        venv_version="$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
        if [ "$venv_version" != "3.12" ]; then
            echo "Existing .venv uses Python $venv_version; recreating it."
            rm -rf .venv
        fi
    fi

    if [ ! -d ".venv" ]; then
        "$python_bin" -m venv .venv
    fi

    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -e .
    python -m pip check
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
    echo "TELEGRAM_API_ID and TELEGRAM_API_HASH: https://my.telegram.org"
    echo "TELEGRAM_BOT_TOKEN: @BotFather"
    echo

    read -r -p "TELEGRAM_API_ID: " TELEGRAM_API_ID
    read -r -p "TELEGRAM_API_HASH: " TELEGRAM_API_HASH
    read -r -p "TELEGRAM_BOT_TOKEN: " TELEGRAM_BOT_TOKEN
    read -r -p "IDS_TO_CHAT, comma-separated: " IDS_TO_CHAT
    read -r -p "MONITOR_CHANNELS, comma-separated, empty = defaults: " MONITOR_CHANNELS
    read -r -p "Use GigaChat filtering? y/n [y]: " USE_GIGACHAT
    USE_GIGACHAT="${USE_GIGACHAT:-y}"

    if [[ "$USE_GIGACHAT" =~ ^[YyДд]$ ]]; then
        GIGACHAT_ENABLED="true"
        read -r -p "GIGACHAT_AUTH_KEY: " GIGACHAT_AUTH_KEY
    else
        GIGACHAT_ENABLED="false"
        GIGACHAT_AUTH_KEY=""
    fi

    export TELEGRAM_API_ID TELEGRAM_API_HASH TELEGRAM_BOT_TOKEN IDS_TO_CHAT
    export MONITOR_CHANNELS GIGACHAT_ENABLED GIGACHAT_AUTH_KEY

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
GIGACHAT_CA_BUNDLE = None

TELEGRAM_SEND_MAX_RETRIES = 3
MESSAGE_QUEUE_SIZE = 100
DELIVERY_RECEIPT_DB_PATH = ".runtime/delivery.sqlite3"
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
    echo "Starting bot..."
    python -m olympiad_news_bot.main
}

install_system_dependencies
clone_or_update_repo
create_virtualenv
create_secrets_if_missing
run_bot
