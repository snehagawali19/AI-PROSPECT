#!/usr/bin/env bash
# Run WITHOUT Docker (macOS/Linux). Creates a venv, installs deps, runs tests, starts the API on :4000.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
[ -f .env ] || cp .env.example .env
python -m pytest
exec uvicorn app.main:app --host 0.0.0.0 --port 4000
