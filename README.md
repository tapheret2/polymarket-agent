# polymarket-agent

**Research-first Polymarket scanning agent** for data-science workflows.

Scan active markets via the public [Gamma API](https://docs.polymarket.com/), score simple research signals, save JSON snapshots, and optionally **paper-trade** into a local ledger. **No private keys. No on-chain orders by default.**

Built for students / builders who care about **AI + markets + data**, not casino bots.

## Features

| Feature | Description |
|--------|-------------|
| **Scan** | Pull active markets (volume-ordered), filter by liquidity |
| **Analyze** | Market mid vs lightweight prior → edge / score / reasons |
| **Snapshot** | JSON dumps under `data/raw/` for later ML / Brier eval |
| **Paper book** | Virtual bankroll fills in `data/processed/paper_book.json` |
| **CLI** | `pm-agent scan`, `search`, `paper-run`, `paper-status` |

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
pm-agent paper-run --max-trades 2
pm-agent paper-status
```

Copy `.env.example` → `.env` to tune bankroll / min liquidity.

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

## Data science roadmap

1. Log daily snapshots → parquet  
2. After resolution, join outcomes → **Brier / log score**  
3. Compare model vs market over time  
4. Optional: CLOB trading (advanced; requires wallet + compliance — out of scope for v0.1)

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
