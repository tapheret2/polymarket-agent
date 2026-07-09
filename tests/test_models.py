import pytest

from polymarket_agent.models import Market


def test_from_gamma_parses_json_strings():
    raw = {
        "id": "abc",
        "question": "Test market?",
        "slug": "test-market",
        "outcomePrices": '["0.6", "0.4"]',
        "clobTokenIds": '["1", "2"]',
        "volume": "1234.5",
        "liquidity": "999",
        "bestBid": "0.59",
        "bestAsk": "0.61",
        "active": True,
        "closed": False,
    }
    m = Market.from_gamma(raw)
    assert m.yes_price == 0.6
    assert m.no_price == 0.4
    assert m.spread == pytest.approx(0.02)
    assert m.volume == 1234.5
