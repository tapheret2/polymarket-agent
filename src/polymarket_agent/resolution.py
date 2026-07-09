from __future__ import annotations

from polymarket_agent.models import Market


def infer_binary_outcome(market: Market) -> int | None:
    """
    Infer YES=1 / NO=0 from closed market prices.
    Returns None if unresolved / void / multi-outcome ambiguous.
    """
    prices = market.outcome_prices
    if not prices:
        return None
    if len(prices) < 2:
        # single price — treat >0.9 as YES
        p = prices[0]
        if p >= 0.9:
            return 1
        if p <= 0.1:
            return 0
        return None

    yes, no = float(prices[0]), float(prices[1])
    # classic resolved books pile mass on one side
    if yes >= 0.9 and no <= 0.1:
        return 1
    if no >= 0.9 and yes <= 0.1:
        return 0
    # both ~0 often means cancelled / legacy junk
    if yes <= 1e-4 and no <= 1e-4:
        return None
    # last trade fallback
    return None


def brier_score(forecast: float, outcome: int) -> float:
    """Brier for a single binary forecast f in [0,1], outcome in {0,1}."""
    f = max(0.0, min(1.0, float(forecast)))
    o = 1.0 if outcome else 0.0
    return (f - o) ** 2


def log_loss(forecast: float, outcome: int, eps: float = 1e-6) -> float:
    import math

    f = max(eps, min(1 - eps, float(forecast)))
    return -math.log(f if outcome else (1 - f))
