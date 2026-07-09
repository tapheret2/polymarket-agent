from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from polymarket_agent.analyzer import rank_signals
from polymarket_agent.client import GammaClient
from polymarket_agent.config import Settings, get_settings
from polymarket_agent.models import Market, Signal
from polymarket_agent.paper import PaperBroker


class PolymarketAgent:
    """
    Research agent loop:
      scan → filter → score → (optional) paper trade top signals
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = GammaClient(self.settings)
        self.paper = PaperBroker(self.settings)

    def close(self) -> None:
        self.client.close()

    def scan(
        self,
        *,
        limit: int | None = None,
        min_liquidity: float | None = None,
        query: str | None = None,
    ) -> list[Market]:
        markets = self.client.list_markets(limit=limit, search=query)
        min_liq = (
            min_liquidity if min_liquidity is not None else self.settings.min_liquidity
        )
        return [
            m
            for m in markets
            if (m.liquidity or 0) >= min_liq and not m.closed and m.yes_price is not None
        ]

    def analyze(self, markets: list[Market]) -> list[Signal]:
        return rank_signals(markets, bankroll=self.paper.book.cash)

    def run_once(
        self,
        *,
        limit: int | None = None,
        top_k: int = 10,
        query: str | None = None,
        paper_trade: bool = False,
        max_paper: int = 3,
    ) -> list[Signal]:
        markets = self.scan(limit=limit, query=query)
        signals = self.analyze(markets)[:top_k]
        if paper_trade:
            traded = 0
            for s in signals:
                if s.side == "HOLD" or s.edge < 0.03:
                    continue
                if traded >= max_paper:
                    break
                try:
                    self.paper.execute(s)
                    traded += 1
                except ValueError:
                    continue
        return signals

    def snapshot(self, signals: list[Signal], path: Path | None = None) -> Path:
        out_dir = self.settings.data_dir / "raw"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = path or out_dir / f"scan_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "n": len(signals),
            "signals": [
                {
                    "question": s.market.question,
                    "slug": s.market.slug,
                    "side": s.side,
                    "market_prob": s.market_prob,
                    "model_prob": s.model_prob,
                    "edge": s.edge,
                    "score": s.score,
                    "liquidity": s.market.liquidity,
                    "volume": s.market.volume,
                    "suggested_stake": s.suggested_stake,
                    "reasons": s.reasons,
                }
                for s in signals
            ],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
