import os
from datetime import date, timedelta
from typing import Any

from dotenv import load_dotenv

from data_collection import collection as collectors
from data_collection.collection.results import CollectionResult
from data_collection.domains import Instrument
from data_collection.providers.mospi import MOSPIProvider
from data_collection.providers.nse_archives import NSEArchivesProvider
from data_collection.providers.nse_filings import NSEFilingsProvider
from data_collection.providers.nse_indices import NSEIndexProvider
from data_collection.providers.nse_public import NSEPublicProvider
from data_collection.providers.rbi import RBIProvider
from data_collection.providers.rss import GoogleNewsRSSProvider, EconomicTimesRSSProvider, BusinessStandardRSSProvider
from data_collection.providers.sebi import SEBIProvider
from data_collection.providers.upstox import UpstoxProvider
from data_collection.providers.yfinance import YahooFinanceProvider
from data_enrichment import EnrichmentProfile, OWNERSHIP_PROFILE, EVENT_PROFILE, REGIME_PROFILE, BENCHMARK_COMPARATIVE_PROFILE, PEER_COMPARATIVE_PROFILE, CORE_MARKET_PROFILE, \
    RELATIVE_MARKET_PROFILE, CORE_FUNDAMENTAL_PROFILE, ProfilePlanner, default_registry, default_profile_registry, execute_plan, EnrichmentContext, ContextPackBuilder, FULL_RESEARCH_CONTEXT, EnrichmentResult
from data_enrichment.profiles.defaults import PRELIMINARY_MARKET_PROFILE
from data_foundation import ingest_collection_results, CanonicalBundle
from data_representation import render_context_pack

load_dotenv()

SCALE_OPTIONS = ['LOW', 'MID', 'HIG']
SCALE_TYPE = {
    'widget_name': 'option_tray',
    'widget_kwargs': {'options': SCALE_OPTIONS},
    'type': str,
}

upstox = UpstoxProvider(os.environ.get("upstox_connector.upstox.anaytics_token"))
yahoo = YahooFinanceProvider()
nse_archives = NSEArchivesProvider()
nse_public = NSEPublicProvider()
nse_index = NSEIndexProvider(nse=nse_public)
nse_filings = NSEFilingsProvider()
rbi = RBIProvider()
mospi = MOSPIProvider()  # TODO: Get token
sebi = SEBIProvider()
rss = [
    GoogleNewsRSSProvider,
    EconomicTimesRSSProvider(),
    BusinessStandardRSSProvider(),
]


def find_instruments(tickers: list[str]) -> list[Instrument]:
    collector = collectors.InstrumentCollector(upstox=upstox, yfinance=yahoo)
    instruments = []
    for ticker in tickers:
        candidates = collector.search_equities(ticker).records
        if len(candidates) > 0:
            instruments.append(candidates[0])
    return instruments


def fetch_data(instrument: Instrument, scale: str, start: date, end: date, period: str) -> tuple[EnrichmentResult, CanonicalBundle]:
    collection: list[CollectionResult[Any]] = []

    market = collectors.MarketCollector(upstox=upstox, yfinance=yahoo, nse=nse_archives)
    fundamentals = collectors.FundamentalsCollector(upstox=upstox)
    shareholding = collectors.ShareholdingCollector(upstox=upstox)
    news = collectors.NewsCollector(yfinance=yahoo)  # , rss_providers=rss
    index_context = collectors.IndexContextCollector(nse=nse_index, archives=nse_archives)
    profiles: list[EnrichmentProfile] = [PRELIMINARY_MARKET_PROFILE]

    collection.append(market.daily_history(instrument, start=start, end=end, period=period))
    collection.append(fundamentals.company_snapshot(instrument.isin, instrument.instrument_id))
    collection.append(news.ticker_news(instrument.symbol))
    collection.append(index_context.sector_classification(instrument.symbol))  # add constituents

    if scale in ('MID', 'HIG'):
        corporate_action = collectors.CorporateActionCollector(upstox=upstox, nse=nse_archives)
        company_event = collectors.CompanyEventCollector(nse=nse_archives)
        ownership = collectors.OwnershipCollector(nse=nse_public)
        filing = collectors.FilingCollector(nse=nse_filings)
        profiles += [CORE_MARKET_PROFILE, CORE_FUNDAMENTAL_PROFILE, OWNERSHIP_PROFILE, EVENT_PROFILE]

        collection.append(fundamentals.company_peers(instrument.isin, instrument.instrument_id))
        collection.append(shareholding.sample(instrument.isin, instrument.instrument_id))
        collection.append(corporate_action.for_instrument(instrument))
        collection.append(company_event.announcements(start, end, instrument=instrument))
        collection.append(company_event.board_meetings(start, end, instrument=instrument))
        collection.append(ownership.shareholding(instrument.symbol))
        collection.append(ownership.insider_transactions(start, end, symbol=instrument.symbol))
        collection.append(filing.financial_results(symbol=instrument.symbol, instrument=instrument))

    if scale == 'HIG':
        macro = collectors.MacroCollector(rbi=rbi, mospi=mospi)
        regulatory = collectors.RegulatoryCollector(sebi=sebi)
        market_events = collectors.MarketEventsCollector(nse=nse_public, nse_archives=nse_archives)
        profiles += [REGIME_PROFILE, BENCHMARK_COMPARATIVE_PROFILE, PEER_COMPARATIVE_PROFILE, RELATIVE_MARKET_PROFILE]

        # collection.append(market_events.archive_daily()) # What to do with trading_date?
        collection.append(market_events.large_deals(mode='bulk_deals', symbol=instrument.symbol))
        collection.append(market_events.large_deals(mode='block_deals', symbol=instrument.symbol))
        collection.append(market_events.large_deals(mode='short_deals', symbol=instrument.symbol))
        collection.append(filing.corporate_announcements(symbol=instrument.symbol, instrument=instrument, from_date=start, to_date=end))
        collection.append(filing.integrated_financials(symbol=instrument.symbol, instrument=instrument, from_date=start, to_date=end))
        collection.append(filing.annual_reports(symbol=instrument.symbol, instrument=instrument))
        collection.append(filing.announcement_xbrl(symbol=instrument.symbol, instrument=instrument, from_date=start, to_date=end))
        collection.append(filing.secretarial_compliance(symbol=instrument.symbol, instrument=instrument))

        # TODO: Make it configurable.
        #  A multi-selection for rbi_table, mospi_cpi, mospi_cpi_item, mospi_iip
        #  and also legal, regulations, circulars, master_circulars, informal_guidance, orders, press_releases, news_listing
        # collection.append(macro.mospi_cpi(Year=str(end.year)))
        # collection.append(regulatory.listing(category=...))

    bundle = ingest_collection_results(collection)
    ctx = EnrichmentContext(
        records=bundle.canonical_records,
        instrument_id=instrument.instrument_id,
        source_observations=bundle.source_observations,
    )
    profile = EnrichmentProfile(
        name='composite',
        enrichers=tuple(dict.fromkeys(enricher for profile in profiles for enricher in profile.enrichers)),
        description='\n'.join(f'{profile.name}\n  {profile.description}' for profile in profiles),
    )
    planner = ProfilePlanner(default_registry(), default_profile_registry())
    plan = planner.plan(profile, available={"price.close"})
    result = execute_plan(ctx, plan)
    return result, bundle


OUTPUT = [
    {'name': 'dataset'},
    {'name': 'status', 'type': str, 'viz': 'side', 'data': 'Hello'},
]


def collect_data(
        *tickers: str,
        scale: SCALE_TYPE = SCALE_OPTIONS[0],
        start: str = str(date.today() - timedelta(weeks=12)),
        end: str = str(date.today()),
        period: str = '1d',
) -> OUTPUT:
    instruments = find_instruments(tickers)
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    dataset = [fetch_data(instrument, scale, start, end, period) for instrument in instruments]
    return {
        'dataset': dataset,
        'hint': 'text',
        'data': f'{'\n'.join([f'{i.name}\n  {i.isin}' for i in instruments])}',
    }


main_callable = collect_data

if __name__ == '__main__':
    data = collect_data("PINELABS", scale='HIG')
    result, bundle = data['dataset'][0]
    pack = ContextPackBuilder().build([result], FULL_RESEARCH_CONTEXT, source_records=bundle.canonical_records)
    print('render', render_context_pack(pack))
