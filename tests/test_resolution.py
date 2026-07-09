from polymarket_agent.models import Market
from polymarket_agent.resolution import brier_score, infer_binary_outcome, log_loss


def test_infer_yes():
    m = Market(question="q", outcomePrices=["0.99", "0.01"])
    assert infer_binary_outcome(m) == 1


def test_infer_no():
    m = Market(question="q", outcomePrices=["0.01", "0.99"])
    assert infer_binary_outcome(m) == 0


def test_infer_void():
    m = Market(question="q", outcomePrices=["0", "0"])
    assert infer_binary_outcome(m) is None


def test_brier_perfect():
    assert brier_score(1.0, 1) == 0.0
    assert brier_score(0.0, 0) == 0.0
    assert brier_score(0.5, 1) == 0.25


def test_log_loss_finite():
    assert log_loss(0.8, 1) > 0
