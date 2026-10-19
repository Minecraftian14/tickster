from datetime import datetime, timezone

from langchain_core.messages import AIMessage

from data_collection.collection.results import CollectionResult
from data_collection.domains import Instrument, PriceBar, Provenance
from data_enrichment import ContextPackBuilder, EnrichmentResult
from exp.exp_tacit_abyss.__main__ import build_demo_graph
from exp.exp_tacit_abyss.data_helper import TACIT_ABYSS_CONTEXT


class FakeModel:
    def invoke(self, prompt):
        if "Portfolio Manager" in prompt:
            return AIMessage(content='{"rating":"Hold","executive_summary":"Wait for confirmation.","investment_thesis":"Evidence is mixed.","key_risks":"Data is incomplete."}')
        if "Trader" in prompt:
            return AIMessage(content='{"action":"Hold","rationale":"No confirmed setup.","entry_price":null,"stop_loss":null,"target_price":null,"allocation_percent":null}')
        return AIMessage(content="Evidence-reviewed report.")


def _context():
    at = datetime(2026, 10, 19, tzinfo=timezone.utc)
    provenance = Provenance(source="fixture", source_type="test", retrieved_at=at)
    instrument = Instrument(instrument_id="NSE:TEST", symbol="TEST", exchange="NSE", name="Test Limited", provenance=provenance)
    bars = [PriceBar(instrument_id="NSE:TEST", timestamp=at, timeframe="1d", close=100 + index, provenance=provenance) for index in range(30)]
    result = EnrichmentResult(enricher="fixture", enricher_version="1")
    pack = ContextPackBuilder().build([result], TACIT_ABYSS_CONTEXT, source_records=[instrument, *bars])
    return pack, (result, type("Bundle", (), {"canonical_records": [instrument, *bars]})())


def test_demo_graph_produces_each_role_history_item():
    state = {"llm": FakeModel(), "message": {"context": _context()}, "history": []}
    final = build_demo_graph().invoke(state)
    names = {item["node_name"] for item in final["history"]}
    assert {"market_analyst", "fundamentals_analyst", "news_analyst", "sentiment_analyst", "bull_researcher", "bear_researcher", "research_manager", "trader", "aggressive_risk_analyst", "conservative_risk_analyst", "neutral_risk_analyst", "portfolio_manager"} <= names
    assert any(item["node_name"] == "trader" and item["output"]["action"] == "Hold" for item in final["history"])
    assert any(item["node_name"] == "portfolio_manager" and item["output"]["rating"] == "Hold" for item in final["history"])


def test_context_profile_declares_social_and_technical_evidence():
    social = next(section for section in TACIT_ABYSS_CONTEXT.sections if section.name == "news_and_social")
    technical = next(section for section in TACIT_ABYSS_CONTEXT.sections if section.name == "derived_market_series")
    assert "SocialPost" in social.source_record_types
    assert "rsi_" in technical.metric_prefixes
