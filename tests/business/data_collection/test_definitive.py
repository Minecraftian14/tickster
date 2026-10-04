import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from data_collection.providers.nse_archives import NSEArchivesProvider
from data_enrichment import EnrichmentContext, ReturnSeriesEnricher, ContextPackBuilder, COMPACT_RESEARCH_CONTEXT, FULL_RESEARCH_CONTEXT
from data_foundation import ingest_collection_results

load_dotenv()

from data_collection.collection import InstrumentCollector, MarketCollector
from data_collection.providers.yfinance import YahooFinanceProvider

from data_collection.providers.upstox import UpstoxProvider


def test_definitive():
    print()

    # Collect the providers which we will use
    upstox = UpstoxProvider(os.environ.get("upstox_connector.upstox.anaytics_token"))
    yahoo = YahooFinanceProvider()
    nse = NSEArchivesProvider()

    # Find or identify Indian equities.
    collector = InstrumentCollector(upstox=upstox)
    instruments = collector.search_equities("RELIANCE")
    for record in instruments.records:
        print("Found", record.name, "with id", record.instrument_id)
    instruments.records = instruments.records[:1] # Retain only the top search
    instrument = instruments.records[0]

    # Call on collectors
    collector = MarketCollector(yfinance=yahoo, upstox=upstox, nse=nse)
    now = datetime.now()
    bars = collector.daily_history(instrument, period="1d", start=now - timedelta(days=7), end=now)

    # Make a bundle of everything
    bundle = ingest_collection_results([instruments, bars])
    print(bundle)

    # Define scope for enrichment
    context = EnrichmentContext(
        bundle.canonical_records,
        # instrument_id="RELIANCE.NS",
        source_observations=bundle.source_observations,
    )

    # Call on enrichers
    result = ReturnSeriesEnricher().enrich(context)

    print(result)
    # print(export_json(result))

    pack = ContextPackBuilder().build([result], FULL_RESEARCH_CONTEXT)
    print(pack)
