#!/usr/bin/env bash
set -e
python -m venv .venv 2>/dev/null || true
. .venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
