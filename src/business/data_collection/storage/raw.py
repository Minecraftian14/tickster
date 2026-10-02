from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from data_collection.collection.results import RawPayload


def stable_json(value: Any) -> str:
    """Serialize a raw payload deterministically for hashing/storage."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def raw_payload_id(item: RawPayload) -> str:
    body = stable_json({"source": item.source, "domain": item.domain, "request": item.request, "payload": item.payload})
    return sha256(body.encode("utf-8")).hexdigest()


def write_raw_payloads(items: Iterable[RawPayload], root: str | Path) -> list[Path]:
    """Persist raw responses as immutable, content-addressed JSON artifacts."""
    root = Path(root)
    written: list[Path] = []
    for item in items:
        digest = raw_payload_id(item)
        timestamp = item.retrieved_at
        target = root / item.source / timestamp.strftime("%Y") / timestamp.strftime("%m") / timestamp.strftime("%d") / f"{digest}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            record = {
                "raw_id": digest,
                "source": item.source,
                "domain": item.domain,
                "retrieved_at": item.retrieved_at.isoformat(),
                "request": item.request,
                "payload": item.payload,
            }
            target.write_text(stable_json(record) + "\n", encoding="utf-8")
        written.append(target)
    return written


def load_raw_payload(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
