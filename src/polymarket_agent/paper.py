from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from polymarket_agent.config import Settings, get_settings
from polymarket_agent.models import PaperBook, PaperFill, Signal


class PaperBroker:
    """Local JSON ledger — no on-chain orders."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.path = Path(self.settings.paper_book_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.book = self._load()

    def _load(self) -> PaperBook:
        if self.path.exists():
            return PaperBook.model_validate_json(self.path.read_text(encoding="utf-8"))
        b = PaperBook(
            bankroll=self.settings.paper_bankroll,
            cash=self.settings.paper_bankroll,
        )
        self._save(b)
        return b

    def _save(self, book: PaperBook | None = None) -> None:
        book = book or self.book
        self.path.write_text(book.model_dump_json(indent=2), encoding="utf-8")

    def execute(self, signal: Signal, size_usd: float | None = None) -> PaperFill:
        if signal.side == "HOLD":
            raise ValueError("cannot paper-trade HOLD")
        price = (
            signal.market.yes_price
            if signal.side == "YES"
            else (signal.market.no_price or 1 - (signal.market.yes_price or 0.5))
        )
        if price is None:
            raise ValueError("missing price")
        notional = size_usd if size_usd is not None else signal.suggested_stake
        if notional <= 0:
            notional = min(10.0, self.book.cash * 0.01)
        if notional > self.book.cash:
            raise ValueError(f"insufficient cash: {self.book.cash:.2f}")

        size_shares = notional / price
        fill = PaperFill(
            ts=datetime.now(timezone.utc),
            market_id=signal.market.id or signal.market.condition_id or signal.market.slug or "?",
            question=signal.market.question,
            side=signal.side,
            price=float(price),
            size=float(size_shares),
            notional=float(notional),
            note=f"edge={signal.edge:.4f}; score={signal.score:.4f}",
        )
        self.book.cash -= notional
        self.book.fills.append(fill)
        self._save()
        return fill

    def summary(self) -> dict:
        spent = sum(f.notional for f in self.book.fills)
        return {
            "bankroll": self.book.bankroll,
            "cash": round(self.book.cash, 2),
            "deployed": round(spent, 2),
            "n_fills": len(self.book.fills),
            "path": str(self.path),
        }

    def export_jsonl(self, path: Path | None = None) -> Path:
        path = path or self.path.with_suffix(".jsonl")
        with path.open("w", encoding="utf-8") as f:
            for fill in self.book.fills:
                f.write(fill.model_dump_json() + "\n")
        return path
