#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f "SECRETS.py" ]; then
    echo "SECRETS.py not found."
    echo "Copy SECRETS.example.py to SECRETS.py and fill real tokens first:"
    echo "  cp SECRETS.example.py SECRETS.py"
    exit 1
fi

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

    echo "Python 3.12 is required, but it was not found." >&2
    echo "Install Python 3.12 and run this script again." >&2
    exit 1
}

PYTHON="$(resolve_python_312)"

if [ -x ".venv/bin/python" ]; then
    VENV_VERSION="$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if [ "$VENV_VERSION" != "3.12" ]; then
        echo "Existing .venv uses Python $VENV_VERSION; recreating it with Python 3.12."
        rm -rf .venv
    fi
fi

if [ ! -d ".venv" ]; then
    echo "Creating Python 3.12 virtual environment..."
    "$PYTHON" -m venv .venv
fi

source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
python -m pip check

mkdir -p .runtime

echo "Starting bot..."
python -m olympiad_news_bot.main
