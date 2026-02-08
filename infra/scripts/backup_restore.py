from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INCLUDE = [
    "data",
    "progress.txt",
    "snapshot.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup/restore helpers for LetterOps.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    backup = sub.add_parser("backup", help="Create a tar.gz backup bundle.")
    backup.add_argument("--output", type=str, default="", help="Backup output path.")
    backup.add_argument(
        "--include",
        action="append",
        default=[],
        help="Relative paths to include (repeatable). Defaults to data + progress/snapshot.",
    )

    restore = sub.add_parser("restore", help="Restore a backup bundle to a target directory.")
    restore.add_argument("archive", type=str, help="Path to .tar.gz backup archive.")
    restore.add_argument("target", type=str, help="Directory to restore into.")

    roundtrip = sub.add_parser("roundtrip", help="Create backup and verify restore round-trip.")
    roundtrip.add_argument(
        "--output",
        type=str,
        default="data/backups/latest.tar.gz",
        help="Backup archive output path.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for item in sorted(path.rglob("*")):
        if item.is_file():
            yield item


def build_manifest(include_paths: list[Path]) -> dict:
    files: list[dict[str, str | int]] = []
    for include in include_paths:
        for file_path in iter_files(include):
            rel = file_path.relative_to(REPO_ROOT)
            files.append(
                {
                    "path": str(rel),
                    "size": file_path.stat().st_size,
                    "sha256": sha256_file(file_path),
                }
            )
    return {"files": files}


def resolve_include(raw: list[str]) -> list[Path]:
    requested = raw or list(DEFAULT_INCLUDE)
    paths: list[Path] = []
    for rel in requested:
        p = (REPO_ROOT / rel).resolve()
        if not p.exists():
            continue
        paths.append(p)
    return paths


def create_backup(output: Path, include_paths: list[Path]) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(include_paths)
    with tempfile.TemporaryDirectory() as td:
        tmp_manifest = Path(td) / "manifest.json"
        tmp_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        with tarfile.open(output, "w:gz") as tar:
            for include in include_paths:
                arcname = include.relative_to(REPO_ROOT)
                tar.add(include, arcname=str(arcname))
            tar.add(tmp_manifest, arcname="manifest.json")
    return output


def restore_backup(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(path=target, filter="data")


def verify_roundtrip(archive: Path) -> dict:
    with tempfile.TemporaryDirectory() as td:
        restore_root = Path(td) / "restore"
        restore_backup(archive, restore_root)
        manifest_path = restore_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        checked = 0
        for item in manifest.get("files", []):
            restored_file = restore_root / item["path"]
            if not restored_file.exists():
                return {"ok": False, "reason": f"Missing file: {item['path']}", "checked": checked}
            if restored_file.stat().st_size != item["size"]:
                return {"ok": False, "reason": f"Size mismatch: {item['path']}", "checked": checked}
            if sha256_file(restored_file) != item["sha256"]:
                return {"ok": False, "reason": f"Checksum mismatch: {item['path']}", "checked": checked}
            checked += 1
        return {"ok": True, "reason": "roundtrip verified", "checked": checked}


def main() -> None:
    args = parse_args()
    if args.cmd == "backup":
        include_paths = resolve_include(args.include)
        out = Path(args.output) if args.output else REPO_ROOT / "data" / "backups" / "latest.tar.gz"
        if not out.is_absolute():
            out = REPO_ROOT / out
        archive = create_backup(out, include_paths)
        print(f"Created backup: {archive}")
        return

    if args.cmd == "restore":
        archive = Path(args.archive)
        if not archive.is_absolute():
            archive = REPO_ROOT / archive
        target = Path(args.target)
        if not target.is_absolute():
            target = REPO_ROOT / target
        restore_backup(archive, target)
        print(f"Restored {archive} -> {target}")
        return

    if args.cmd == "roundtrip":
        out = Path(args.output)
        if not out.is_absolute():
            out = REPO_ROOT / out
        include_paths = resolve_include([])
        archive = create_backup(out, include_paths)
        result = verify_roundtrip(archive)
        print(json.dumps(result, indent=2))
        if not result["ok"]:
            raise SystemExit(1)
        return

    raise SystemExit(2)


if __name__ == "__main__":
    main()
