from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_id(*parts: Any) -> str:
    body = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
