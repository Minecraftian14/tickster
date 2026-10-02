from data_collection.providers.upstox import UpstoxProvider


def test_upstox_fundamental_paths(monkeypatch):
    calls = []
    provider = UpstoxProvider("test-token")
    def fake_get(path, params=None):
        calls.append((path, params))
        return {"status": "success", "data": {}}
    monkeypatch.setattr(provider, "_get", fake_get)

    provider.income_statement("INE002A01018", full_statement=True)
    provider.cash_flow("INE002A01018", full_statement=True)
    provider.key_ratios("INE002A01018")
    provider.share_holdings("INE002A01018")

    assert calls[0][0].endswith("/income-statement")
    assert calls[0][1]["fs"] == "true"
    assert calls[1][0].endswith("/cash-flow")
    assert calls[2][0].endswith("/key-ratios")
    assert calls[3][0].endswith("/share-holdings")
