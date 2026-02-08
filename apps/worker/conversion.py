from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apps.worker.storage_service import build_derived_path, ensure_parent_dir


@dataclass(frozen=True)
class ConversionResult:
    txt_path: Path | None
    md_path: Path | None
    errors: list[str]


def write_txt(doc_id: str, text: str) -> Path:
    path = build_derived_path(doc_id, "txt")
    ensure_parent_dir(path)
    path.write_text(text, encoding="utf-8")
    return path


def write_md(doc_id: str, text: str) -> Path:
    path = build_derived_path(doc_id, "md")
    ensure_parent_dir(path)
    content = text
    path.write_text(content, encoding="utf-8")
    return path


def convert_text(doc_id: str, text: str) -> ConversionResult:
    errors: list[str] = []
    txt_path = None
    md_path = None

    try:
        txt_path = write_txt(doc_id, text)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"txt:{exc}")

    try:
        md_path = write_md(doc_id, text)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"md:{exc}")

    return ConversionResult(txt_path=txt_path, md_path=md_path, errors=errors)
