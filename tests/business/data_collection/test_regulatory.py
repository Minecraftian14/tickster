from datetime import datetime, timezone

from data_collection.collection.regulatory import RegulatoryCollector
from data_collection.domains.regulatory import RegulatoryItem
from data_collection.processing.regulatory import deduplicate_regulatory, group_regulatory_by_category, titles_containing
from data_collection.providers.sebi import SEBIProvider, next_page_url, parse_detail_html, parse_listing_html

NOW = datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)

LISTING_FIXTURE = b'''<html><body>
<table><tr><th>Date</th><th>Title</th></tr>
<tr><td>Oct 01, 2026</td><td><a href="/legal/doc1">SEBI Circular on Listed Entities</a></td></tr>
<tr><td>Sep 30, 2026</td><td><a href="/legal/doc2">Review of Disclosure Requirements</a></td></tr>
</table>
<a href="/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&pageno=2">Next</a>
</body></html>'''

DETAIL_FIXTURE = b'''<html><head><title>SEBI Circular on Listed Entities</title></head><body>
<h1>SEBI Circular on Listed Entities</h1>
<a href="/filings/example.pdf">PDF</a>
<a href="/filings/example.xml">XBRL</a>
</body></html>'''


def test_parse_listing_extracts_date_title_and_detail_url():
    rows = parse_listing_html(LISTING_FIXTURE, category="circulars", page_url="https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes")
    assert len(rows) == 2
    assert rows[0]["title"] == "SEBI Circular on Listed Entities"
    assert rows[0]["detail_url"] == "https://www.sebi.gov.in/legal/doc1"
    assert rows[0]["published_at"] == datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_next_page_url_is_followed_from_visible_next_link():
    url = next_page_url(LISTING_FIXTURE, page_url="https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes")
    assert url == "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&pageno=2"


def test_parse_detail_extracts_document_links():
    data = parse_detail_html(DETAIL_FIXTURE, detail_url="https://www.sebi.gov.in/legal/doc1")
    assert data["title"] == "SEBI Circular on Listed Entities"
    urls = {x["url"] for x in data["document_links"]}
    assert "https://www.sebi.gov.in/filings/example.pdf" in urls
    assert "https://www.sebi.gov.in/filings/example.xml" in urls


def test_provider_listing_uses_configurable_client():
    class FakeResponse:
        status_code = 200
        headers = {"content-type": "text/html"}
        url = "https://example.test/list"
        text = LISTING_FIXTURE.decode()
        def raise_for_status(self):
            pass

    class FakeClient:
        def get(self, url):
            assert "example.test" in url
            return FakeResponse()

    provider = SEBIProvider(base_url="https://example.test", client=FakeClient())
    rows, requests = provider.listing("circulars", max_pages=1)
    assert len(rows) == 2
    assert requests[0]["status_code"] == 200


def test_regulatory_collector_reports_missing_provider():
    result = RegulatoryCollector().listing("circulars")
    assert result.errors[0]["source"] == "sebi"


def test_regulatory_processing_helpers():
    p = RegulatoryItem(
        regulatory_id="x", category="orders", title="Order in the matter of Reliance",
        provenance={"source": "sebi", "source_type": "regulator", "retrieved_at": NOW},
    )
    q = p.model_copy(update={"title": "Order in the matter of Reliance revised"})
    assert len(deduplicate_regulatory([p, q])) == 1
    grouped = group_regulatory_by_category([p])
    assert list(grouped) == ["orders"]
    assert titles_containing([p], "reliance") == [p]
