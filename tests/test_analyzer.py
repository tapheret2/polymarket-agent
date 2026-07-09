from polymarket_agent.analyzer import score_market
from polymarket_agent.models import Market


def test_score_market_hold_or_side():
    m = Market(
        question="Will unit tests pass?",
        slug="unit-tests",
        outcomePrices=["0.55", "0.45"],
        liquidity=5000,
        volume=10000,
        bestBid=0.54,
        bestAsk=0.56,
    )
    s = score_market(m, bankroll=1000)
    assert s.market_prob == 0.55
    assert s.side in {"YES", "NO", "HOLD"}
    assert isinstance(s.edge, float)
    assert s.reasons


def test_low_liquidity_marked():
    m = Market(
        question="Illiquid joke market",
        outcomePrices=["0.8", "0.2"],
        liquidity=50,
        volume=10,
    )
    s = score_market(m)
    assert any("low_liquidity" in r for r in s.reasons)
