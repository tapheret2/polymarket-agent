#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
else
  PY=python3
fi
"$PY" -m polymarket_agent.cli daily-scan --limit 50 --top 20
"$PY" -m polymarket_agent.cli eval
