from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from polymarket_agent.models import Market, Signal


def _clamp(p: float, lo: float = 0.02, hi: float = 0.98) -> float:
    return max(lo, min(hi, p))


def days_to_end(market: Market, now: datetime | None = None) -> float | None:
    if not market.end_date:
        return None
    now = now or datetime.now(timezone.utc)
    end = market.end_date
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return (end - now).total_seconds() / 86400.0


def baseline_model_prob(market: Market) -> tuple[float, list[str]]:
    """
    Lightweight research prior — NOT alpha by itself.

    Starts at market mid, then applies soft adjustments from liquidity,
    time-to-resolution, and extreme prices (favorite-longshot style caution).
    """
    reasons: list[str] = []
    mid = market.yes_price
    if mid is None:
        return 0.5, ["missing_price"]

    p = float(mid)
    reasons.append(f"market_mid={p:.3f}")

    # Prefer liquid markets: shrink less when liquidity is high
    liq = market.liquidity or 0.0
    vol = market.volume or 0.0
    if liq < 500:
        p = 0.5 + (p - 0.5) * 0.7
        reasons.append("low_liquidity_shrink")
    elif liq > 20_000:
        reasons.append("high_liquidity")

    if vol < 1_000:
        reasons.append("low_volume_flag")

    # Near-certain prices: slight mean reversion for research score only
    if p > 0.9:
        p = p - 0.02
        reasons.append("fade_extreme_yes_slightly")
    elif p < 0.1:
        p = p + 0.02
        reasons.append("fade_extreme_no_slightly")

    dte = days_to_end(market)
    if dte is not None:
        reasons.append(f"days_to_end={dte:.1f}")
        if dte < 0:
            reasons.append("past_end_date")
        elif dte < 1 and 0.35 < p < 0.65:
            # coin-flip near resolution often noise
            p = 0.5 + (p - 0.5) * 0.85
            reasons.append("near_resolution_noise_shrink")

    # Keyword caution for joke/illiquid cultural markets
    q = (market.question or "").lower()
    if re.search(r"\b(gta|rihanna|alien|illuminati)\b", q):
        reasons.append("entertainment_market")

    return _clamp(p), reasons


def score_market(market: Market, bankroll: float = 1000.0) -> Signal:
    mid = market.yes_price or 0.5
    model_p, reasons = baseline_model_prob(market)
    edge_yes = model_p - mid
    edge_no = (1 - model_p) - (market.no_price or (1 - mid))

    # Choose side with positive edge
    if edge_yes >= edge_no and edge_yes > 0:
        side, edge, mprob = "YES", edge_yes, model_p
    elif edge_no > edge_yes and edge_no > 0:
        side, edge, mprob = "NO", edge_no, 1 - model_p
    else:
        side, edge, mprob = "HOLD", max(edge_yes, edge_no, 0.0), model_p

    spread = market.spread or 0.0
    liq = math.log10(max(market.liquidity or 1.0, 1.0))
    # Composite: edge minus half-spread, scaled by liquidity
    score = (edge - 0.5 * spread) * (1 + 0.15 * liq)

    # Fractional Kelly-ish paper stake (very conservative)
    stake = 0.0
    if side != "HOLD" and edge > 0.02:
        # b ≈ (1-price)/price for binary long; use price as cost
        price = mid if side == "YES" else (market.no_price or 1 - mid)
        price = max(0.05, min(0.95, price))
        # edge in probability space → rough f = edge / odds
        f = min(0.05, max(0.0, edge / max(1 - price, 0.05)) * 0.25)
        stake = round(bankroll * f, 2)
        reasons.append(f"paper_fraction={f:.4f}")

    if spread and spread > 0.08:
        reasons.append("wide_spread")
        if side != "HOLD":
            score *= 0.7

    return Signal(
        market=market,
        side=side,
        market_prob=float(mid),
        model_prob=float(mprob if side != "NO" else model_p),
        edge=float(edge),
        score=float(score),
        reasons=reasons,
        suggested_stake=stake,
    )


def rank_signals(markets: list[Market], bankroll: float = 1000.0) -> list[Signal]:
    signals = [score_market(m, bankroll=bankroll) for m in markets]
    return sorted(signals, key=lambda s: s.score, reverse=True)
