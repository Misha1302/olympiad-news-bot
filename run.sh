#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f "SECRETS.py" ]; then
    echo "SECRETS.py not found."
    echo "Copy SECRETS.example.py to SECRETS.py and fill real tokens first:"
    echo "  cp SECRETS.example.py SECRETS.py"
    exit 1
fi

if command -v python3.12 >/dev/null 2>&1; then
    PYTHON="python3.12"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    echo "Python 3 is not installed."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

mkdir -p .runtime

echo "Starting bot..."
PYTHONPATH=src python -m olympiad_news_bot.main
