from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd


class RBIProvider:
    """Lightweight adapter for RBI's DBIE export/download model.

    DBIE exposes pre-formatted reports that can be exported to CSV/XLS/XLSX/PDF.
    This adapter intentionally works with exported tabular artifacts instead of
    pretending there is one stable public JSON API for every DBIE series.
    """

    name = "rbi"
    source_type = "primary_macro"

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "installed": True,
            "mode": "dbie_export_or_url",
            "formats": ["csv", "xls", "xlsx"],
        }

    @staticmethod
    def fetch_bytes(url: str, *, timeout: int = 30, headers: dict[str, str] | None = None) -> bytes:
        request = Request(url, headers=headers or {"User-Agent": "indian-equity-data-platform/0.9"})
        with urlopen(request, timeout=timeout) as response:
            return response.read()

    @staticmethod
    def read_table(source: str | Path | bytes, *, format_hint: str | None = None, **kwargs: Any) -> pd.DataFrame:
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.exists():
                payload = path.read_bytes()
                inferred = format_hint or path.suffix.lstrip(".")
            else:
                payload = RBIProvider.fetch_bytes(str(source))
                inferred = format_hint or str(source).split("?")[0].rsplit(".", 1)[-1]
        else:
            payload = source
            inferred = format_hint or "csv"

        fmt = inferred.lower().replace(".", "")
        if fmt == "csv":
            return pd.read_csv(BytesIO(payload), **kwargs)
        if fmt in {"xls", "xlsx", "excel"}:
            return pd.read_excel(BytesIO(payload), **kwargs)
        raise ValueError(f"Unsupported RBI table format: {inferred}")
