from data_enrichment import FinanceToolkitBackend, QuantStatsBackend, PandasTABackend


def test_backend_capabilities_are_non_overlapping_by_intent():
    finance = FinanceToolkitBackend()
    quant = QuantStatsBackend()
    ta = PandasTABackend()
    assert "valuation" in finance.capabilities
    assert "risk" in quant.capabilities
    assert "rsi" in ta.capabilities
    assert ta.supports("rsi") is True
    assert ta.supports("not-a-capability") is False
