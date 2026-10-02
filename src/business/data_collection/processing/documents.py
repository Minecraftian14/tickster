from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
import re

from data_collection.domains.filings import DocumentAsset, XBRLFact


def infer_document_type(*, url: str | None = None, mime_type: str | None = None) -> str:
    value = f"{mime_type or ''} {url or ''}".lower()
    if "pdf" in value or value.rstrip().endswith(".pdf"):
        return "pdf"
    if "xml" in value or "xbrl" in value:
        return "xbrl_xml"
    if "xlsx" in value or "spreadsheetml" in value or value.rstrip().endswith(".xls"):
        return "xlsx"
    if "zip" in value:
        return "zip"
    if "csv" in value:
        return "csv"
    if "html" in value or ".htm" in value:
        return "html"
    if "text/plain" in value or ".txt" in value:
        return "text"
    return "unknown"


def extract_pdf_text(path: str | Path) -> str:
    """Extract text from a PDF using pypdf.

    Kept optional at import time so collection does not require a PDF package.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF text extraction") from exc
    reader = PdfReader(str(path))
    parts: list[str] = []
    for index, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"--- Page {index} ---\n{text.strip()}")
    return "\n\n".join(parts)


def extract_html_text(path: str | Path) -> str:
    """Extract visible text from simple HTML without requiring BeautifulSoup."""
    from html.parser import HTMLParser

    class TextParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []
            self._skip = 0

        def handle_starttag(self, tag, attrs):
            if tag.lower() in {"script", "style", "noscript"}:
                self._skip += 1

        def handle_endtag(self, tag):
            if tag.lower() in {"script", "style", "noscript"} and self._skip:
                self._skip -= 1

        def handle_data(self, data):
            if not self._skip and data.strip():
                self.parts.append(data.strip())

    parser = TextParser()
    parser.feed(Path(path).read_text(encoding="utf-8", errors="replace"))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(parser.parts)).strip()


def parse_xbrl_facts(
    xml_bytes: bytes,
    *,
    filing_id: str | None = None,
    instrument_id: str | None = None,
    provenance: Any,
    include_raw_xml: bool = False,
    issues: list[dict[str, Any]] | None = None,
) -> list[XBRLFact]:
    """Parse XBRL facts while preserving context, dimensions and raw concepts.

    This is deliberately taxonomy-agnostic. Financial concept mapping belongs
    in a later enrichment layer.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        if issues is not None:
            issues.append({"source": getattr(provenance, "source", "unknown"), "operation": "parse_xbrl_facts", "message": str(exc), "error_type": type(exc).__name__})
        raise
    contexts: dict[str, dict[str, Any]] = {}
    units: dict[str, str] = {}

    ns = {
        "xbrli": "http://www.xbrl.org/2003/instance",
        "xbrldi": "http://xbrl.org/2006/xbrldi",
    }

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def text_or_none(node: ET.Element | None) -> str | None:
        return None if node is None else (node.text or "").strip() or None

    for child in root.iter():
        lname = local(child.tag)
        if lname == "context":
            ctx_id = child.attrib.get("id")
            if not ctx_id:
                continue
            info: dict[str, Any] = {"dimensions": {}}
            period = next((n for n in child.iter() if local(n.tag) == "period"), None)
            if period is not None:
                start = next((n for n in period if local(n.tag) == "startDate"), None)
                end = next((n for n in period if local(n.tag) == "endDate"), None)
                instant = next((n for n in period if local(n.tag) == "instant"), None)
                info["period_start"] = _parse_date(text_or_none(start))
                info["period_end"] = _parse_date(text_or_none(end))
                info["instant"] = _parse_date(text_or_none(instant))
            for node in child.iter():
                if local(node.tag) in {"explicitMember", "typedMember"}:
                    dim = node.attrib.get("dimension")
                    value = text_or_none(node)
                    if dim and value:
                        info["dimensions"][local(dim)] = value.rsplit("}", 1)[-1]
            contexts[ctx_id] = info
        elif lname == "unit":
            unit_id = child.attrib.get("id")
            if unit_id:
                measure = next((n for n in child.iter() if local(n.tag) == "measure"), None)
                units[unit_id] = text_or_none(measure) or unit_id

    facts: list[XBRLFact] = []
    xbrli_namespace = ns["xbrli"]
    known_container_names = {
        "xbrl", "context", "unit", "schemaRef", "footnoteLink",
        "labelLink", "referenceLink", "roleRef", "arcroleRef",
    }

    for elem in root.iter():
        lname = local(elem.tag)
        if lname in known_container_names:
            continue
        context_ref = elem.attrib.get("contextRef")
        if not context_ref:
            continue
        # Ignore inline-XBRL containers and nested presentation structures.
        if elem.tag.startswith("{") and elem.tag.split("}", 1)[0][1:] == xbrli_namespace:
            continue
        value_text = (elem.text or "").strip()
        if not value_text and list(elem):
            if issues is not None:
                issues.append({"source": getattr(provenance, "source", "unknown"), "operation": "parse_xbrl_facts", "message": "Skipped nested XBRL element without scalar text", "concept": lname})
            continue
        context = contexts.get(context_ref, {})
        raw_value: Any = value_text
        fact_format = elem.attrib.get("{http://www.xbrl.org/2008/inlineXBRL}format")
        if elem.attrib.get("nil") == "true" or elem.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}nil") == "true":
            raw_value = None
        else:
            raw_value = _coerce_numeric(value_text, decimals=elem.attrib.get("decimals"), scale=elem.attrib.get("scale"))

        raw_xml = ET.tostring(elem, encoding="unicode") if include_raw_xml else None
        concept = elem.tag.rsplit("}", 1)[-1]
        facts.append(XBRLFact(
            filing_id=filing_id,
            instrument_id=instrument_id,
            concept=concept,
            value=raw_value,
            context_ref=context_ref,
            unit_ref=elem.attrib.get("unitRef"),
            decimals=elem.attrib.get("decimals"),
            period_start=context.get("period_start"),
            period_end=context.get("period_end"),
            instant=context.get("instant"),
            dimensions=context.get("dimensions", {}),
            raw_xml=raw_xml,
            provenance=provenance,
            metadata={"fact_format": fact_format, "unit": units.get(elem.attrib.get("unitRef", ""))},
        ))
    return facts


def xbrl_facts_to_markdown(facts: list[XBRLFact], title: str = "XBRL Facts") -> str:
    lines = [f"# {title}", "", "| Concept | Period | Value | Unit | Dimensions |", "|---|---|---:|---|---|"]
    for fact in facts:
        period = fact.instant.isoformat() if fact.instant else (
            f"{fact.period_start.isoformat()}→{fact.period_end.isoformat()}"
            if fact.period_start and fact.period_end else (fact.period_end.isoformat() if fact.period_end else "")
        )
        unit = str((fact.metadata or {}).get("unit") or fact.unit_ref or "")
        dims = ", ".join(f"{k}={v}" for k, v in fact.dimensions.items())
        value = "" if fact.value is None else str(fact.value).replace("|", "\\|")
        lines.append(f"| `{fact.concept}` | {period} | {value} | {unit} | {dims} |")
    return "\n".join(lines)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _coerce_numeric(value: str, *, decimals: str | None, scale: str | None) -> Any:
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        number = Decimal(cleaned)
    except Exception:
        return value
    if scale not in (None, "", "0"):
        try:
            number *= Decimal(10) ** int(scale)
        except Exception:
            pass
    # Keep integers as int; other numbers as Decimal for exactness.
    if number == number.to_integral():
        return int(number)
    return number
