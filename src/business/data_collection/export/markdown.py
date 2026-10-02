from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


_SCALAR_TYPES = (str, int, float, bool, type(None))


def _is_scalar(value: Any) -> bool:
    return isinstance(value, _SCALAR_TYPES)


def _is_pydantic_model(value: Any) -> bool:
    return callable(getattr(value, "model_dump", None))


def _coerce(value: Any) -> Any:
    """Convert common structured Python objects to JSON-like values.

    This deliberately uses duck-typing so the renderer does not require pandas,
    pydantic, numpy, or other project-specific dependencies.
    """
    if _is_pydantic_model(value):
        return _coerce(value.model_dump(mode="python"))

    if is_dataclass(value) and not isinstance(value, type):
        return _coerce(asdict(value))

    # pandas DataFrame / Series are detected lazily and therefore remain optional.
    module = type(value).__module__
    name = type(value).__name__
    if module.startswith("pandas") and name == "DataFrame":
        return {
            "__markdown_dataframe__": True,
            "columns": [str(column) for column in value.columns],
            "rows": [list(row) for row in value.itertuples(index=False, name=None)],
        }
    if module.startswith("pandas") and name == "Series":
        return {
            "__markdown_series__": True,
            "name": None if value.name is None else str(value.name),
            "rows": [[index, item] for index, item in value.items()],
        }

    if isinstance(value, Mapping):
        return {str(key): _coerce(item) for key, item in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_coerce(item) for item in value]

    # Numpy-like scalar values and other scalar-ish objects commonly expose an
    # item() method. Use it only when it actually returns a different value.
    item = getattr(value, "item", None)
    if callable(item):
        try:
            result = item()
        except Exception:  # pragma: no cover - defensive fallback
            result = value
        if result is not value:
            return _coerce(result)

    return value


def _escape_inline(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _display_scalar(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _is_scalar_matrix(rows: list[Any]) -> bool:
    if not rows or not all(isinstance(row, Sequence) and not isinstance(row, (str, bytes, bytearray)) for row in rows):
        return False
    widths = {len(row) for row in rows}
    return len(widths) == 1 and all(_is_scalar(cell) for row in rows for cell in row)


def _render_table(headers: Sequence[Any], rows: Sequence[Sequence[Any]]) -> list[str]:
    header_values = [_escape_inline(_display_scalar(value)) for value in headers]
    width = len(header_values)
    normalized_rows: list[list[str]] = []
    for row in rows:
        cells = [_escape_inline(_display_scalar(cell)) for cell in row]
        if len(cells) < width:
            cells.extend([""] * (width - len(cells)))
        normalized_rows.append(cells[:width])

    lines = [f"| {' | '.join(header_values)} |", f"| {' | '.join('---' for _ in range(width))} |"]
    lines.extend(f"| {' | '.join(row)} |" for row in normalized_rows)
    return lines


def _dict_is_all_scalar(obj: Mapping[str, Any]) -> bool:
    return bool(obj) and all(_is_scalar(value) for value in obj.values())


def _records_as_table(items: list[Any]) -> tuple[list[str], list[list[Any]]] | None:
    if not items or not all(isinstance(item, Mapping) for item in items):
        return None
    records = [dict(item) for item in items]

    # A table is used only when every cell is scalar. This avoids silently
    # stringifying nested structures into opaque cells.
    if not all(all(_is_scalar(value) for value in record.values()) for record in records):
        return None

    # Preserve the first-seen key order across records.
    headers: list[str] = []
    for record in records:
        for key in record:
            if key not in headers:
                headers.append(str(key))

    rows = [[record.get(header) for header in headers] for record in records]
    return headers, rows


def _render_list(items: list[Any], level: int) -> list[str]:
    if not items:
        return ["- _empty_"]

    if _is_scalar_matrix(items):
        rows = [list(row) for row in items]
        width = len(rows[0])
        headers = [f"Column {index + 1}" for index in range(width)]
        return _render_table(headers, rows)

    table = _records_as_table(items)
    if table is not None:
        headers, rows = table
        return _render_table(headers, rows)

    if all(_is_scalar(item) for item in items):
        return [f"- {_escape_inline(_display_scalar(item))}" for item in items]

    lines: list[str] = []
    for index, item in enumerate(items, 1):
        lines.append(f"- **Item {index}**")
        child_lines = _render_value(item, level + 1, heading_for_value=False)
        if child_lines:
            lines.extend("  " + line if line else "" for line in child_lines)
    return lines


def _render_object(obj: Mapping[str, Any], level: int) -> list[str]:
    """Render a mapping whose nested keys occupy headings at *level*."""
    if obj.get("__markdown_dataframe__"):
        return _render_table(obj["columns"], obj["rows"])
    if obj.get("__markdown_series__"):
        name = obj.get("name") or "value"
        return _render_table(["Index", name], obj["rows"])

    lines: list[str] = []
    scalar_items = [(str(key), value) for key, value in obj.items() if _is_scalar(value)]
    complex_items = [(str(key), value) for key, value in obj.items() if not _is_scalar(value)]

    # A single scalar is clearer as a recursively-headed leaf and matches the
    # simple structural rule: {"a":{"b":{"c":"d"}}} -> # a / ## b / ### c / d.
    if len(scalar_items) == 1 and not complex_items:
        key, value = scalar_items[0]
        lines.append(f"{'#' * max(1, level)} {_escape_inline(key)}")
        lines.append("")
        lines.append(_escape_inline(_display_scalar(value)))
        return lines

    if scalar_items:
        lines.extend(_render_table(["Field", "Value"], scalar_items))
        if complex_items:
            lines.append("")

    for index, (key, value) in enumerate(complex_items):
        if index:
            lines.append("")
        lines.append(f"{'#' * max(1, level)} {_escape_inline(key)}")
        lines.append("")
        if isinstance(value, Mapping):
            lines.extend(_render_object(value, level + 1))
        elif isinstance(value, list):
            lines.extend(_render_list(value, level + 1))
        else:
            lines.extend(_render_value(value, level + 1, heading_for_value=False))

    return lines

def _render_value(value: Any, level: int, *, heading_for_value: bool, key: str | None = None) -> list[str]:
    value = _coerce(value)

    if _is_scalar(value):
        return [_escape_inline(_display_scalar(value))]

    if isinstance(value, Mapping):
        return _render_object(value, level)

    if isinstance(value, list):
        return _render_list(value, level)

    return [_escape_inline(_display_scalar(value))]


def render_markdown(data: Any, *, title: str | None = None) -> str:
    """Render arbitrary JSON-like data into readable, structured Markdown.

    Rules:
      * dictionaries: scalar fields become a compact key/value table;
        nested values become recursive headings;
      * homogeneous scalar-record lists become tables;
      * rectangular lists of scalars become tables;
      * scalar lists become bullet lists;
      * nested/heterogeneous lists become nested bullet structures;
      * pandas DataFrame/Series are rendered as tables when pandas is installed.

    The function is intentionally domain-agnostic and preserves structure rather
    than interpreting domain-specific field names.
    """
    value = _coerce(data)
    lines: list[str] = []

    if title is not None:
        lines.extend([f"# {_escape_inline(title)}", ""])

    if isinstance(value, Mapping):
        lines.extend(_render_object(value, 2 if title else 1))
    elif isinstance(value, list):
        lines.extend(_render_list(value, 2 if title else 1))
    else:
        lines.extend(_render_value(value, 1, heading_for_value=False))

    # Normalize excess blank lines without touching intentional table/list lines.
    text = "\n".join(lines).strip()
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text + "\n"


def render_markdown_raw_json(data: Any, *, title: str | None = None) -> str:
    """Render JSON-like data using the project's legacy JSON-in-code-block style."""
    payload = _coerce(data)
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    prefix = f"# {_escape_inline(title)}\n\n" if title is not None else ""
    return f"{prefix}```json\n{body}\n```\n"


def write_markdown(data: Any, path: str | Path, *, title: str | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(data, title=title), encoding="utf-8")
    return path


def models_to_markdown(
    title: str,
    items: Iterable[Any],
    path: str | Path,
    *,
    mode: str = "structured",
) -> Path:
    """Compatibility wrapper for the existing collection export API.

    mode='structured' uses the generic recursive renderer.
    mode='raw' retains the previous JSON-code-block behavior.
    """
    materialized = [_coerce(item) for item in items]
    if mode == "structured":
        content = render_markdown(materialized, title=title)
    elif mode == "raw":
        # Preserve the historical 'Record N' framing for apples-to-apples experiments.
        lines = [f"# {_escape_inline(title)}", ""]
        for index, item in enumerate(materialized, 1):
            lines.extend([f"## Record {index}", "", "```json", json.dumps(item, ensure_ascii=False, indent=2, default=str), "```", ""])
        content = "\n".join(lines).rstrip() + "\n"
    else:
        raise ValueError("mode must be 'structured' or 'raw'")

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
