from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from apps.worker.hashing import sha256_file
from apps.worker.worker_config import settings


class StorageError(RuntimeError):
    pass


def build_original_path(doc_id: str, original_filename: str, event_time: datetime) -> Path:
    date_path = event_time.strftime("%Y/%m/%d")
    return settings.archive_originals_dir / date_path / doc_id / original_filename


def build_derived_path(doc_id: str, extension: str) -> Path:
    extension = extension.lstrip(".")
    return settings.archive_derived_dir / doc_id / f"{doc_id}.{extension}"


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def store_original(src_path: Path, dest_path: Path) -> str:
    ensure_parent_dir(dest_path)
    if dest_path.exists():
        src_hash = sha256_file(src_path)
        dest_hash = sha256_file(dest_path)
        if src_hash != dest_hash:
            raise StorageError(
                f"Original file already exists with different checksum: {dest_path}"
            )
        return dest_hash

    shutil.copy2(src_path, dest_path)
    return sha256_file(dest_path)
