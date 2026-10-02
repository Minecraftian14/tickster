from datetime import datetime, timedelta, timezone
import pytest
from data_foundation import CanonicalRecord
from data_enrichment import (
    EnrichmentContext, HistoricalStateSummaryEnricher, TrendRegimeEnricher,
    VolatilityRegimeEnricher, ExtremesRegimeEnricher, PersistenceRegimeEnricher,
    REGIME_PROFILE, default_registry, EnrichmentPipeline
)
BASE=datetime(2020,1,1,tzinfo=timezone.utc)
def bar(i, close):
    ts=BASE+timedelta(days=i)
    return CanonicalRecord(record_id=f'r{i}', domain='market', record_type='PriceBar', payload={
        'instrument_id':'REL','timestamp':ts,'close':close,'published_at':ts
    })
def ctx(records): return EnrichmentContext(records, instrument_id='REL')

def test_historical_state_multiple_horizons_and_percentile():
    recs=[bar(i, 100*(1.0005**i)) for i in range(1500)]
    r=HistoricalStateSummaryEnricher().enrich(ctx(recs))
    assert {s.summary_type for s in r.summaries} >= {'historical_state_1y','historical_state_3y','historical_percentiles'}
    one=next(s for s in r.summaries if s.summary_type=='historical_state_1y')
    assert one.values['observations']==252
    assert 0 <= next(s for s in r.summaries if s.summary_type=='historical_percentiles').values['close_percentile_1y'] <= 100

def test_trend_state_strong_up():
    recs=[bar(i,100+i) for i in range(260)]
    r=TrendRegimeEnricher().enrich(ctx(recs))
    assert r.summaries[0].values['state']=='strong_up'

def test_volatility_state_low_for_constant_growth():
    recs=[bar(i,100*(1.001**i)) for i in range(400)]
    r=VolatilityRegimeEnricher(volatility_window=20, history_window=252).enrich(ctx(recs))
    assert r.summaries[0].values['state'] in {'low','normal','high'}
    assert 0 <= r.summaries[0].values['historical_percentile'] <= 100

def test_extremes_and_persistence():
    closes=[100,110,120,115,125,130,128,140]
    recs=[bar(i,v) for i,v in enumerate(closes)]
    ext=ExtremesRegimeEnricher().enrich(ctx(recs)).summaries[0].values
    assert ext['all_time_high']==140
    assert ext['all_time_low']==100
    per=PersistenceRegimeEnricher(ma_window=3).enrich(ctx(recs)).summaries[0].values
    assert per['positive_return_fraction'] > 0.5
    assert per['current_above_ma'] is True

def test_regime_profile_registered_and_plannable():
    reg=default_registry()
    for name in REGIME_PROFILE.enrichers:
        assert reg.get(name).version=='0.6.0'
    recs=[bar(i,100+i) for i in range(300)]
    out=EnrichmentPipeline(reg).run(ctx(recs), list(REGIME_PROFILE.enrichers), available={'price.close'})
    assert not [x for x in out.issues if x.severity=='error']

def test_historical_state_respects_as_of_and_excludes_future_records():
    recs = [bar(i, 100 + i) for i in range(500)]
    cutoff = BASE + timedelta(days=200, hours=12)
    out = HistoricalStateSummaryEnricher(horizons=(("window", 252),)).enrich(
        EnrichmentContext(recs, instrument_id="REL", as_of=cutoff)
    )
    summary = next(item for item in out.summaries if item.summary_type == "historical_state_window")
    assert summary.values["end_close"] == 300
    assert summary.values["observations"] == 201
    assert summary.lineage.source_record_ids[-1] == "r200"


def test_extremes_respect_as_of():
    recs = [bar(i, 100 + i) for i in range(500)]
    cutoff = BASE + timedelta(days=100, hours=12)
    out = ExtremesRegimeEnricher().enrich(EnrichmentContext(recs, instrument_id="REL", as_of=cutoff))
    values = out.summaries[0].values
    assert values["all_time_high"] == 200
    assert values["all_time_low"] == 100
