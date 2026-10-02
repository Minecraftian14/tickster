from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel

from .models import CanonicalRecord, RawArtifact, SourceObservation


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _safe_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value).strip())
    return cleaned or "unknown"


def _raw_extension(media_type: str) -> str:
    mapping = {
        "application/json": ".json",
        "application/xml": ".xml",
        "text/xml": ".xml",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "text/html": ".html",
        "application/pdf": ".pdf",
        "application/zip": ".zip",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-excel": ".xls",
    }
    return mapping.get(media_type.lower(), ".bin")


def _write_jsonl(items: Iterable[BaseModel], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            handle.write(item.model_dump_json(exclude_none=False) + "\n")
    return path


def write_raw_artifact(
    content: bytes | bytearray | memoryview | str | Any,
    root: str | Path,
    *,
    source: str,
    domain: str,
    retrieved_at: datetime,
    media_type: str = "application/octet-stream",
    source_url: str | None = None,
    metadata: dict[str, Any] | None = None,
    artifact_id: str | None = None,
) -> RawArtifact:
    """Persist immutable content-addressed raw evidence and return its metadata."""
    if isinstance(content, (bytes, bytearray, memoryview)):
        payload = bytes(content)
    elif isinstance(content, str):
        payload = content.encode("utf-8")
    else:
        payload = _stable_json(content)
        if media_type == "application/octet-stream":
            media_type = "application/json"

    digest = sha256(payload).hexdigest()
    root = Path(root)
    # The bytes are content-addressed by their exact content hash. Retrieval date
    # is metadata, not part of the content path, so the same bytes are stored once.
    relative = Path("raw") / _safe_segment(source) / digest[:2] / f"{digest}{_raw_extension(media_type)}"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(payload)

    return RawArtifact(
        artifact_id=artifact_id or digest,
        source=source,
        domain=domain,
        media_type=media_type,
        content_hash=digest,
        size_bytes=len(payload),
        storage_path=relative.as_posix(),
        retrieved_at=retrieved_at,
        source_url=source_url,
        metadata=metadata or {},
    )


def write_raw_manifest(artifacts: Iterable[RawArtifact], root: str | Path) -> Path:
    return _write_jsonl(artifacts, Path(root) / "indexes" / "raw_artifacts.jsonl")


def write_canonical_records(items: Iterable[CanonicalRecord], root: str | Path, *, domain: str | None = None) -> Path:
    items = list(items)
    selected_domain = domain or (items[0].domain if items else "unknown")
    return _write_jsonl(items, Path(root) / "canonical" / _safe_segment(selected_domain) / "records.jsonl")


def write_source_observations(items: Iterable[SourceObservation], root: str | Path) -> Path:
    return _write_jsonl(items, Path(root) / "canonical" / "_source_observations" / "records.jsonl")


def write_canonical_indexes(
    records: Iterable[CanonicalRecord],
    observations: Iterable[SourceObservation],
    root: str | Path,
) -> dict[str, Path]:
    records = list(records)
    observations = list(observations)
    canonical_to_obs: list[dict[str, Any]] = []
    observation_to_raw: list[dict[str, Any]] = []
    for record in records:
        for observation_id in record.source_observation_ids:
            canonical_to_obs.append({"record_id": record.record_id, "observation_id": observation_id})
    for observation in observations:
        if observation.raw_ref:
            observation_to_raw.append({"observation_id": observation.observation_id, "raw_artifact_id": observation.raw_ref})

    index_dir = Path(root) / "indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    a = index_dir / "canonical_to_observations.jsonl"
    b = index_dir / "observation_to_raw.jsonl"
    with a.open("a", encoding="utf-8") as handle:
        for row in canonical_to_obs:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with b.open("a", encoding="utf-8") as handle:
        for row in observation_to_raw:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return {"canonical_to_observations": a, "observation_to_raw": b}


def write_canonical_jsonl(items: Iterable[BaseModel], root: str | Path, *, domain: str) -> Path:
    """Backward-compatible canonical JSONL writer."""
    return _write_jsonl(items, Path(root) / "canonical" / _safe_segment(domain) / "records.jsonl")


def write_manifest(manifest: dict[str, Any], root: str | Path) -> Path:
    root = Path(root)
    path = root / "indexes" / "foundation_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_raw_artifact(root: str | Path, artifact: RawArtifact) -> bytes:
    """Load the exact raw bytes referenced by a RawArtifact."""
    path = Path(root) / artifact.storage_path
    data = path.read_bytes()
    if sha256(data).hexdigest() != artifact.content_hash:
        raise ValueError(f"Raw artifact integrity check failed: {artifact.artifact_id}")
    return data
