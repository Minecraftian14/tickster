from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pydantic import BaseModel


def write_jsonl(items: Iterable[BaseModel], path: str | Path) -> Path:
    path: Path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(item.model_dump_json() + "\n")
    return path
