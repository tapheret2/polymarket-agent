# polymarket-agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/tapheret2/polymarket-agent?style=social)](https://github.com/tapheret2/polymarket-agent/stargazers)
![status](https://img.shields.io/badge/status-active-brightgreen) ![python](https://img.shields.io/badge/python-3.10%2B-blue) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

**Research-first Polymarket scanning agent** for data-science workflows.

Scan active markets via the public [Gamma API](https://docs.polymarket.com/), score simple research signals, save JSON snapshots, and optionally **paper-trade** into a local ledger. **No private keys. No on-chain orders by default.**

Built for students / builders who care about **AI + markets + data**, not casino bots.

## Features

| Feature | Description |
|--------|-------------|
| **Scan** | Pull active markets (volume-ordered), filter by liquidity |
| **Analyze** | Market mid vs lightweight prior → edge / score / reasons |
| **Snapshot** | JSON dumps under `data/raw/` for later ML / Brier eval |
| **Eval** | Join snapshots to resolved markets → **Brier / log-loss** |
| **Daily job** | `pm-agent daily-scan` (+ PowerShell/bash scripts, Docker) |
| **Paper book** | Virtual bankroll fills in `data/processed/paper_book.json` |
| **CLI** | `scan`, `search`, `daily-scan`, `eval`, `paper-run`, `paper-status` |

> **Disclaimer:** Educational / research software. Prediction markets involve risk of loss. This is **not** financial advice. The baseline model is intentionally simple — beat it with your own models.

## Quickstart

```bash
# Python 3.11+
git clone https://github.com/tapheret2/polymarket-agent.git
cd polymarket-agent

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -e ".[dev]"
# or: pip install -r requirements.txt && pip install -e .

pm-agent scan --limit 40 --top 15
pm-agent search "bitcoin"
pm-agent daily-scan
pm-agent eval --closed-benchmark
pm-agent paper-run --max-trades 2
pm-agent paper-status
```

Copy `.env.example` → `.env` to tune bankroll / min liquidity.

### Docker

```bash
docker build -t polymarket-agent .
docker run --rm -v "${PWD}/data:/app/data" polymarket-agent daily-scan
docker run --rm -v "${PWD}/data:/app/data" polymarket-agent eval
```

### Windows daily schedule

```powershell
# Task Scheduler → Action:
powershell -File C:\Users\ADMIN\projects\polymarket-agent\scripts\daily_scan.ps1
```

## Architecture

```
src/polymarket_agent/
  client.py      # Gamma HTTP client (User-Agent + retries)
  models.py      # Market / Signal / PaperBook (pydantic)
  analyzer.py    # baseline prior + ranking
  paper.py       # local JSON paper broker
  agent.py       # scan → analyze → paper loop
  cli.py         # Typer + Rich
```

### Signal logic (v0.1)

Starts from market mid price, then soft adjustments:

- Shrink toward 0.5 when **liquidity is low**
- Mild fade of **extreme** prices (favorite-longshot caution)
- Near-resolution noise shrink for coin-flip mids
- Score ≈ `(edge − ½ spread) × liquidity factor`
- Paper stake ≈ **very fractional** Kelly-style (cap 5% bankroll)

Replace `baseline_model_prob` with your DS model (calibration, LLM features, ensembles).

## Data science loop (built-in)

1. **`daily-scan`** logs forecasts under `data/raw/scan_*.json`  
2. **`eval`** joins to resolved markets → Brier / log-loss under `data/processed/eval_*.json`  
3. Compare `brier_model` vs `brier_market` over weeks  
4. Swap `baseline_model_prob` for your model when it beats the market on eval  

Optional later: parquet export, CLOB live trading (wallet + compliance — not in v0.1.x).

## Tests

```bash
pytest -q
pytest -q -m integration   # hits live Gamma API
```

## Security

- No ClawHub trading-bot skills / no wallet managers  
- Paper mode only writes local JSON  
- Do not commit `.env` or API secrets  

## License

MIT © 2026 Phạm Tiến Phát ([@tapheret2](https://github.com/tapheret2))

## Related

If you use [Grok](https://x.ai) / agent skills locally, pair this repo with research skills (`polymarket`, `prediction-markets`, `ds-project`) for writeups — code lives here.

## Why this repo
- Research-first Polymarket scanning (not a black-box trading bot)
- Paper-trading friendly workflow for DS students
- Reproducible scans under `data/`

## Quick demo
```bash
pip install -e ".[dev]"
# see README install section for full CLI
pytest -q
```

Educational only — not financial advice.
