from data_collection.collection.results import CollectionResult, RawPayload


def test_collection_result_accumulates_records_raw_and_errors():
    result = CollectionResult(domain="market")
    result.records.append("record")
    result.raw_payloads.append(RawPayload(source="x", domain="market", retrieved_at=result.collected_at, payload={"x": 1}))
    result.errors.append({"source": "y", "error": "boom"})
    assert result.domain == "market"
    assert result.records == ["record"]
    assert result.raw_payloads[0].payload["x"] == 1
    assert result.errors[0]["source"] == "y"
