from data_foundation.quality import classify_missing, summarize_quality


def test_quality_distinguishes_unknown_from_present():
    unknown = classify_missing(None, source="nse", field="foo")
    present = classify_missing(0, source="nse", field="foo")
    summary = summarize_quality([unknown, present])
    assert unknown.status == "unknown"
    assert present.status == "present"
    assert summary == {"unknown": 1, "present": 1}
