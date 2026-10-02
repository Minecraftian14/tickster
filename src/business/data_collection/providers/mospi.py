from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class MOSPIProvider:
    """Adapter for official MOSPI e-Sankhyiki APIs.

    Current MOSPI documentation exposes CPI and IIP APIs. Authentication is
    optional for the first limited response; callers can supply a bearer token
    obtained from the MOSPI authentication flow for larger queries.
    """

    name = "mospi"
    source_type = "primary_macro"
    default_base_url = "https://api.mospi.gov.in"

    def __init__(self, *, token: str | None = None, base_url: str | None = None):
        self.token = token
        self.base_url = (base_url or self.default_base_url).rstrip("/")

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "installed": True,
            "token_configured": bool(self.token),
            "apis": ["cpi", "iip"],
        }

    def get_json(self, path: str, *, params: dict[str, Any] | None = None, timeout: int = 30) -> Any:
        query = urlencode({k: v for k, v in (params or {}).items() if v is not None})
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        headers = {"Accept": "application/json", "User-Agent": "indian-equity-data-platform/0.9"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(url, headers=headers)
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def cpi_index(self, **params: Any) -> Any:
        return self.get_json("/api/getCPIIndex", params=params)

    def cpi_item_index(self, **params: Any) -> Any:
        return self.get_json("/api/getItemIndex", params=params)

    def iip(self, **params: Any) -> Any:
        return self.get_json("/api/iip/getIIPData", params=params)
