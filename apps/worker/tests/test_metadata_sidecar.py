from pathlib import Path

from apps.worker.metadata_sidecar import write_metadata


def test_write_metadata(tmp_path: Path) -> None:
    path = write_metadata("doc1", 1, {"a": 1}, base_dir=tmp_path)
    assert path.exists()
    assert path.read_text(encoding="utf-8").strip().startswith("{")
