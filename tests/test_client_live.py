"""Optional live tests — skip if network blocked."""

import httpx
import pytest

from polymarket_agent.client import GammaClient


@pytest.mark.integration
def test_list_markets_live():
    try:
        with GammaClient() as c:
            markets = c.list_markets(limit=5)
    except httpx.HTTPError as e:
        pytest.skip(f"network/API unavailable: {e}")
    assert len(markets) >= 1
    assert markets[0].question
    assert markets[0].yes_price is not None
