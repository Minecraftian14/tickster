from datetime import datetime, timedelta, timezone
from decimal import Decimal

from data_collection.domains import PriceBar, Provenance
from data_enrichment.core.context import EnrichmentContext
from data_enrichment.market.technical import TechnicalIndicatorEnricher


def _bars(count):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    provenance = Provenance(source="fixture", source_type="test", retrieved_at=now)
    return [PriceBar(instrument_id="NSE:TEST", timestamp=now + timedelta(days=index), timeframe="1d", close=Decimal(100 + index), provenance=provenance) for index in range(count)]


def test_technical_indicators_produce_rsi_and_macd():
    result = TechnicalIndicatorEnricher().enrich(EnrichmentContext(records=_bars(40), instrument_id="NSE:TEST"))
    assert {series.metric for series in result.series} == {"rsi_14", "macd", "macd_signal"}
    assert result.summaries[0].summary_type == "technical_indicators"


def test_technical_indicators_report_insufficient_data():
    result = TechnicalIndicatorEnricher().enrich(EnrichmentContext(records=_bars(3), instrument_id="NSE:TEST"))
    assert result.issues[0].code == "insufficient_observations"
