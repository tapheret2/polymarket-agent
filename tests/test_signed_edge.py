from polymarket_agent.analyzer import signed_edge, edge_passes

def test_signed_edge():
    assert abs(signed_edge(0.6, 0.5) - 0.1) < 1e-12

def test_edge_passes():
    assert edge_passes(0.6, 0.5, min_abs=0.05)
    assert not edge_passes(0.52, 0.5, min_abs=0.05)
