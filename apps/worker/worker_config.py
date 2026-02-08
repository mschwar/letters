from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkerSettings:
    repo_root: Path
    data_dir: Path
    archive_originals_dir: Path
    archive_derived_dir: Path
    metadata_dir: Path
    runs_dir: Path

    @staticmethod
    def load() -> "WorkerSettings":
        repo_root = Path(__file__).resolve().parents[2]
        data_dir = repo_root / "data"
        return WorkerSettings(
            repo_root=repo_root,
            data_dir=data_dir,
            archive_originals_dir=data_dir / "archive" / "originals",
            archive_derived_dir=data_dir / "archive" / "derived",
            metadata_dir=data_dir / "metadata",
            runs_dir=data_dir / "runs",
        )


settings = WorkerSettings.load()
