from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


def _parse_jsonish(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


class Market(BaseModel):
    """Normalized Polymarket market snapshot."""

    id: str | None = None
    condition_id: str | None = Field(default=None, alias="conditionId")
    question: str
    slug: str | None = None
    description: str | None = None
    end_date: datetime | None = Field(default=None, alias="endDate")
    active: bool | None = True
    closed: bool | None = False
    volume: float | None = 0.0
    liquidity: float | None = 0.0
    best_bid: float | None = Field(default=None, alias="bestBid")
    best_ask: float | None = Field(default=None, alias="bestAsk")
    outcome_prices: list[float] = Field(default_factory=list, alias="outcomePrices")
    outcomes: list[str] = Field(default_factory=list)
    clob_token_ids: list[str] = Field(default_factory=list, alias="clobTokenIds")
    raw: dict[str, Any] = Field(default_factory=dict, exclude=True)

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @field_validator("outcome_prices", mode="before")
    @classmethod
    def parse_prices(cls, v: Any) -> Any:
        v = _parse_jsonish(v)
        if v is None:
            return []
        if isinstance(v, list):
            out: list[float] = []
            for x in v:
                try:
                    out.append(float(x))
                except (TypeError, ValueError):
                    continue
            return out
        return v

    @field_validator("outcomes", "clob_token_ids", mode="before")
    @classmethod
    def parse_str_lists(cls, v: Any) -> Any:
        v = _parse_jsonish(v)
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return v

    @field_validator("volume", "liquidity", "best_bid", "best_ask", mode="before")
    @classmethod
    def parse_float(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    @property
    def yes_price(self) -> float | None:
        if self.outcome_prices:
            return float(self.outcome_prices[0])
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        return self.best_ask or self.best_bid

    @property
    def no_price(self) -> float | None:
        if len(self.outcome_prices) > 1:
            return float(self.outcome_prices[1])
        yp = self.yes_price
        return 1.0 - yp if yp is not None else None

    @property
    def spread(self) -> float | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return max(0.0, float(self.best_ask) - float(self.best_bid))

    @classmethod
    def from_gamma(cls, payload: dict[str, Any]) -> "Market":
        data = dict(payload)
        # Gamma sometimes nests event fields
        if not data.get("question") and data.get("title"):
            data["question"] = data["title"]
        return cls.model_validate({**data, "raw": payload})


class Signal(BaseModel):
    market: Market
    side: str  # YES | NO | HOLD
    market_prob: float
    model_prob: float
    edge: float
    score: float
    reasons: list[str] = Field(default_factory=list)
    suggested_stake: float = 0.0


class PaperFill(BaseModel):
    ts: datetime
    market_id: str
    question: str
    side: str
    price: float
    size: float
    notional: float
    note: str = ""


class PaperBook(BaseModel):
    bankroll: float
    cash: float
    fills: list[PaperFill] = Field(default_factory=list)
