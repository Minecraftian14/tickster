from datetime import date, datetime, timezone

from data_collection.collection.filings import FilingCollector, _records_from_payload
from data_collection.domains.models import Instrument, Provenance
from data_collection.processing.documents import infer_document_type, parse_xbrl_facts, xbrl_facts_to_markdown
from data_collection.providers.nse_filings import NSEFilingsProvider


NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)


def instrument():
    return Instrument(
        instrument_id="INE002A01018", isin="INE002A01018", symbol="RELIANCE", exchange="NSE",
        instrument_key="NSE_EQ|INE002A01018",
        provenance=Provenance(source="test", source_type="fixture", retrieved_at=NOW),
    )


def test_nse_filing_provider_builds_asset_type():
    asset = NSEFilingsProvider.asset_from_url(
        "https://nsearchives.nseindia.com/annual_reports/AR_123_RELIANCE_2025.pdf",
        title="Annual Report", instrument=instrument(), retrieved_at=NOW
    )
    assert asset.document_type == "pdf"
    assert asset.instrument_id == instrument().instrument_id
    assert asset.asset_id.startswith("nse:")


def test_integrated_result_catalog_normalization():
    class StubNSE:
        def integrated_filing_results(self, **kwargs):
            return {"data": [{
                "symbol": "RELIANCE",
                "companyName": "Reliance Industries Limited",
                "quarterEndDate": "30-Jun-2026",
                "typeOfSubmission": "Original",
                "audited": "Unaudited",
                "consolidated": "Consolidated",
                "broadcastDateTime": "24-Sep-2026 20:56:32",
                "xbrl": "https://nsearchives.nseindia.com/corporate/x.xml",
                "details": "https://nsearchives.nseindia.com/corporate/details.pdf",
            }]}
    result = FilingCollector(nse=StubNSE()).integrated_financials(
        symbol="RELIANCE", instrument=instrument(), page=1, size=50
    )
    assert not result.errors
    assert len(result.records) == 1
    filing = result.records[0]
    assert filing.period_end == date(2026, 6, 30)
    assert filing.statement_type == "Consolidated"
    assert filing.audited is False
    assert len(filing.assets) == 2
    assert result.raw_payloads[0].request["endpoint"] == "integrated-filing-results"


def test_legacy_financial_results_preserve_point_in_time_fields():
    class StubNSE:
        def financial_results(self, **kwargs):
            return [{
                "symbol": "RELIANCE",
                "period": "Quarterly",
                "toDate": "31-Mar-2025",
                "filingDate": "22-Apr-2025 18:10:00",
                "consolidated": "Standalone",
                "xbrl": "https://nsearchives.nseindia.com/corporate/r.xml",
            }]
    result = FilingCollector(nse=StubNSE()).financial_results(symbol="RELIANCE", instrument=instrument())
    filing = result.records[0]
    assert filing.period_end == date(2025, 3, 31)
    assert filing.published_at == datetime(2025, 4, 22, 18, 10, tzinfo=timezone.utc)
    assert filing.metadata["raw"]["filingDate"].startswith("22-Apr-2025")


def test_xbrl_parser_is_taxonomy_agnostic():
    xml = b"""<?xml version="1.0"?>
    <xbrl xmlns="http://www.xbrl.org/2003/instance"
          xmlns:ex="http://example.com/ex">
      <context id="c1"><entity><identifier>INE002A01018</identifier></entity>
        <period><startDate>2026-04-01</startDate><endDate>2026-06-30</endDate></period></context>
      <unit id="INR"><measure>iso4217:INR</measure></unit>
      <ex:Revenue contextRef="c1" unitRef="INR" decimals="0">123456</ex:Revenue>
      <ex:TextFact contextRef="c1">hello</ex:TextFact>
    </xbrl>"""
    facts = parse_xbrl_facts(
        xml,
        filing_id="f1",
        instrument_id=instrument().instrument_id,
        provenance=Provenance(source="nse", source_type="primary_exchange", retrieved_at=NOW),
    )
    assert len(facts) == 2
    revenue = next(f for f in facts if f.concept == "Revenue")
    assert revenue.value == 123456
    assert revenue.period_end == date(2026, 6, 30)
    text = next(f for f in facts if f.concept == "TextFact")
    assert text.value == "hello"
    assert "Revenue" in xbrl_facts_to_markdown(facts)


def test_document_type_inference():
    assert infer_document_type(url="https://example/x.pdf") == "pdf"
    assert infer_document_type(url="https://example/x.xml") == "xbrl_xml"
    assert infer_document_type(mime_type="text/html") == "html"


def test_nested_payload_record_extraction():
    payload = {"outer": {"filings": [{"symbol": "TCS"}, {"symbol": "INFY"}]}}
    assert _records_from_payload(payload) == [{"symbol": "TCS"}, {"symbol": "INFY"}]


def test_corporate_announcement_catalog_preserves_attachments_and_published_time():
    class StubNSE:
        def corporate_announcements(self, **kwargs):
            return [{
                "symbol": "RELIANCE",
                "sm_name": "Reliance Industries Limited",
                "desc": "Press Release",
                "attchmntText": "Reliance Industries Limited has informed the Exchange...",
                "attchmntFile": "https://nsearchives.nseindia.com/corporate/rel.pdf",
                "an_dt": "30-Sep-2026 18:20:00",
                "exchdisstime": "30-Sep-2026 18:20:02",
                "sm_isin": "INE002A01018",
            }]
    result = FilingCollector(nse=StubNSE()).corporate_announcements(
        symbol="RELIANCE", from_date=date(2026, 9, 30), to_date=date(2026, 9, 30), instrument=instrument()
    )
    assert not result.errors
    filing = result.records[0]
    assert filing.category == "corporate_announcements"
    assert filing.subcategory == "Press Release"
    assert filing.published_at == datetime(2026, 9, 30, 18, 20, tzinfo=timezone.utc)
    assert len(filing.assets) == 1


def test_nse_xbrl_filing_inventory_is_broad_and_filterable():
    from data_collection.domains.filing_catalog import list_nse_xbrl_filing_families
    all_families = list_nse_xbrl_filing_families()
    capital_raising = list_nse_xbrl_filing_families(capability_group="capital_raising")
    assert len(all_families) >= 50
    assert any(item["key"] == "related_party_transactions" for item in all_families)
    assert any(item["key"] == "brsr" for item in all_families)
    assert len(capital_raising) >= 5
