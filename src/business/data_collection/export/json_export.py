from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _is_hashable(value):
    try:
        hash(value)
        return True
    except TypeError:
        return False


def _redump(obj:Any):
    return json.loads(json.dumps(obj, ensure_ascii=False, indent=2, default=conversion_helper))

def _export_field(obj: Any):
    if isinstance(obj, list) and len(obj) > 1 and all(type(obj[0]) == type(x) for x in obj[1:]):
        obj = list(map(_redump, obj))
        if not all(isinstance(x, dict) for x in obj): return obj
        common_keys = set(obj[0]).intersection(*(d.keys() for d in obj))
        common_keys = {key for key in common_keys
                       if all(_is_hashable(d[key]) and d[key] == obj[0][key] for d in obj)}
        return {
            "header": {k: obj[0][k] for k in common_keys},
            "entries": [{k: _redump(v) for k, v in d.items() if k not in common_keys} for d in obj]
        }
    return _redump(obj)


def conversion_helper(obj: Any):
    # // TODO: skip derived_id,metadata recursively
    if hasattr(obj, "export_to_raw"):
        return getattr(obj, "export_to_raw")(_redump)
    elif isinstance(obj, BaseModel):
        result = obj.model_dump(exclude_none=True)
        if "derived_id" in result: del result["derived_id"]
        if "metadata" in result: del result["metadata"]
        if "provenance" in result: del result["provenance"]
        return result
    return str(obj)


def export_json(payload: Any, path: str | Path = None) -> Path:
    content = json.dumps(payload, ensure_ascii=False, indent=2, default=conversion_helper)
    if path is None:
        return content
    else:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path
