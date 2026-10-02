from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pydantic import BaseModel


def models_to_markdown(title: str, items: Iterable[BaseModel], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for i, item in enumerate(items, 1):
        lines.append(f"## Record {i}")
        lines.append("```json")
        lines.append(item.model_dump_json(indent=2))
        lines.append("```")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
