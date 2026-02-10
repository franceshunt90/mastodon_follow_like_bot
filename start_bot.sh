#!/usr/bin/env bash
# Start script: will use local .venv if present, otherwise install requirements and run
set -e
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [ -d "$PROJECT_DIR/.venv" ]; then
	source "$PROJECT_DIR/.venv/bin/activate"
else
	python3 -m venv .venv
	source .venv/bin/activate
	pip install --upgrade pip
	pip install -r requirements.txt
fi

python mastodon_bot.py
