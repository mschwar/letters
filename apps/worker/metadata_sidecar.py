from __future__ import annotations

import json
from pathlib import Path

from apps.worker.worker_config import settings


def metadata_path(doc_id: str, version_no: int, base_dir: Path | None = None) -> Path:
    root = base_dir or settings.metadata_dir
    return root / doc_id / f"metadata.v{version_no}.json"


def write_metadata(doc_id: str, version_no: int, payload: dict, base_dir: Path | None = None) -> Path:
    path = metadata_path(doc_id, version_no, base_dir=base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing.strip() == serialized.strip():
            return path
    path.write_text(serialized, encoding="utf-8")
    return path
