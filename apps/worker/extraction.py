from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


DATE_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})"),
]


@dataclass(frozen=True)
class ExtractedMetadata:
    document_date: str | None
    source_name: str | None
    audience: str | None
    document_type: str | None
    canonical_title: str | None
    summary_one_sentence: str | None
    confidence_by_field: dict[str, float]

    def overall_confidence(self) -> float:
        if not self.confidence_by_field:
            return 0.0
        return min(self.confidence_by_field.values())


@dataclass(frozen=True)
class ExtractedContent:
    text: str
    metadata: ExtractedMetadata


def _read_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf_text(path)
    if suffix in {".txt", ".md"}:
        return _read_text_file(path)
    return _read_text_file(path)


def _find_date(text: str) -> tuple[str | None, float]:
    iso_match = DATE_PATTERNS[0].search(text)
    if iso_match:
        year, month, day = iso_match.groups()
        return f"{year}-{month}-{day}", 0.9

    named_match = DATE_PATTERNS[1].search(text)
    if named_match:
        month_name, day, year = named_match.groups()
        try:
            parsed = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y")
            return parsed.strftime("%Y-%m-%d"), 0.7
        except ValueError:
            pass
    return None, 0.0


def _guess_source(text: str) -> tuple[str | None, float]:
    for source in [
        "Universal House of Justice",
        "National Spiritual Assembly",
        "Local Spiritual Assembly",
        "Bahá'í International Community",
    ]:
        if source.lower() in text.lower():
            return source, 0.6
    return None, 0.0


def _summary_from_text(text: str) -> tuple[str | None, float]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None, 0.0
    summary = lines[0]
    return summary[:240], 0.4


def extract_metadata(text: str) -> ExtractedMetadata:
    document_date, date_conf = _find_date(text)
    source_name, source_conf = _guess_source(text)
    summary, summary_conf = _summary_from_text(text)

    confidence = {
        "document_date": date_conf,
        "source_name": source_conf,
        "summary_one_sentence": summary_conf,
    }

    return ExtractedMetadata(
        document_date=document_date,
        source_name=source_name,
        audience=None,
        document_type=None,
        canonical_title=None,
        summary_one_sentence=summary,
        confidence_by_field=confidence,
    )


def extract_content(path: Path) -> ExtractedContent:
    text = extract_text(path)
    metadata = extract_metadata(text)
    return ExtractedContent(text=text, metadata=metadata)
