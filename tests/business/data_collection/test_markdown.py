from __future__ import annotations

from pathlib import Path

import pytest

from data_collection.export.markdown import (
    models_to_markdown,
    render_markdown,
    render_markdown_raw_json,
    write_markdown,
)


def test_nested_objects_become_recursive_sections() -> None:
    markdown = render_markdown({"a": {"b": {"c": "d"}}})
    assert "# a" in markdown
    assert "## b" in markdown
    assert "### c" in markdown
    assert markdown.rstrip().endswith("d")


def test_scalar_object_becomes_key_value_table() -> None:
    markdown = render_markdown({"symbol": "RELIANCE", "exchange": "NSE", "active": True})
    assert "| Field | Value |" in markdown
    assert "| symbol | RELIANCE |" in markdown
    assert "| active | true |" in markdown


def test_list_of_atoms_becomes_bullets() -> None:
    markdown = render_markdown({"tags": ["energy", "large-cap", "india"]})
    assert "- energy" in markdown
    assert "- large-cap" in markdown
    assert "- india" in markdown
    assert "| Field | Value |" not in markdown


def test_list_of_scalar_records_becomes_table() -> None:
    markdown = render_markdown(
        {
            "prices": [
                {"date": "2026-09-29", "close": 103.0, "volume": 1500},
                {"date": "2026-09-30", "close": 101.0, "volume": 1800},
            ]
        }
    )
    assert "| date | close | volume |" in markdown
    assert "| 2026-09-30 | 101.0 | 1800 |" in markdown


def test_rectangular_list_of_lists_becomes_table() -> None:
    markdown = render_markdown({"matrix": [[1, 2], [3, 4]]})
    assert "| Column 1 | Column 2 |" in markdown
    assert "| 3 | 4 |" in markdown


def test_ragged_nested_list_remains_nested() -> None:
    markdown = render_markdown({"data": [[1, 2], [3, [4, 5]]]})
    assert "| Column 1 | Column 2 |" not in markdown
    assert "**Item 1**" in markdown
    assert "**Item 2**" in markdown


def test_nested_record_list_does_not_stringify_nested_objects() -> None:
    markdown = render_markdown(
        {
            "events": [
                {"name": "A", "details": {"kind": "one"}},
                {"name": "B", "details": {"kind": "two"}},
            ]
        }
    )
    assert "{\"kind\": \"one\"}" not in markdown
    assert "**Item 1**" in markdown
    assert "kind" in markdown


def test_dataframe_is_rendered_as_table() -> None:
    pd = pytest.importorskip("pandas")
    frame = pd.DataFrame({"date": ["2026-09-29", "2026-09-30"], "close": [103.0, 101.0]})
    markdown = render_markdown({"prices": frame})
    assert "| date | close |" in markdown
    assert "| 2026-09-30 | 101.0 |" in markdown


def test_series_is_rendered_as_two_column_table() -> None:
    pd = pytest.importorskip("pandas")
    series = pd.Series([10, 11], index=["A", "B"], name="score")
    markdown = render_markdown({"scores": series})
    assert "| Index | score |" in markdown
    assert "| B | 11 |" in markdown


def test_raw_json_mode_is_available_for_experiments() -> None:
    markdown = render_markdown_raw_json({"a": {"b": 1}}, title="Example")
    assert markdown.startswith("# Example")
    assert '"b": 1' in markdown
    assert "```json" in markdown


def test_models_to_markdown_structured_and_raw(tmp_path: Path) -> None:
    structured = tmp_path / "structured.md"
    raw = tmp_path / "raw.md"

    models_to_markdown("Records", [{"x": 1}, {"x": 2}], structured, mode="structured")
    models_to_markdown("Records", [{"x": 1}, {"x": 2}], raw, mode="raw")

    assert "| x |" in structured.read_text(encoding="utf-8")
    raw_text = raw.read_text(encoding="utf-8")
    assert "## Record 1" in raw_text
    assert "```json" in raw_text


def test_write_markdown(tmp_path: Path) -> None:
    output = write_markdown({"hello": {"world": "ok"}}, tmp_path / "out.md", title="Test")
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert text.startswith("# Test")
    assert "world" in text
