from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader


DATE_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})"),
    re.compile(r"(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})"),
]

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


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
        values = list(self.confidence_by_field.values())
        return sum(values) / len(values)


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

    dmy_match = DATE_PATTERNS[2].search(text)
    if dmy_match:
        day, month_name, year = dmy_match.groups()
        try:
            parsed = datetime.strptime(f"{day} {month_name} {year}", "%d %B %Y")
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


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML-like frontmatter key-value pairs and return (fields, body)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end():]
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        if value:
            fields[key.strip()] = value
    return fields, body


def _summary_from_text(text: str, body: str | None = None) -> tuple[str | None, float]:
    source = body if body is not None else text
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if not lines:
        return None, 0.0
    summary = lines[0]
    if len(summary) < 10 and len(lines) > 1:
        summary = lines[1]
    return summary[:240], 0.5


def _guess_title(text: str, body: str | None = None) -> tuple[str | None, float]:
    """Derive a title from the first substantive heading or line of the body."""
    source = body if body is not None else text
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Markdown heading
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title[:200], 0.6
        # Skip very short lines (e.g. author names, dates)
        if len(stripped) < 8:
            continue
        # Use first substantive line as title
        return stripped[:200], 0.4
    return None, 0.0


def extract_metadata(text: str) -> ExtractedMetadata:
    frontmatter, body = _parse_frontmatter(text)

    # Prefer frontmatter date, fall back to regex scan
    fm_date = frontmatter.get("date")
    if fm_date:
        # Try to parse frontmatter date as ISO
        iso_match = DATE_PATTERNS[0].search(fm_date)
        if iso_match:
            document_date = iso_match.group(0)
            date_conf = 0.95
        else:
            # Try "Month DD, YYYY"
            named_match = DATE_PATTERNS[1].search(fm_date)
            if named_match:
                month_name, day, year = named_match.groups()
                try:
                    parsed = datetime.strptime(f"{month_name} {day} {year}", "%B %d %Y")
                    document_date = parsed.strftime("%Y-%m-%d")
                    date_conf = 0.85
                except ValueError:
                    document_date = fm_date
                    date_conf = 0.5
            else:
                # Try "DD Month YYYY"
                dmy_match = DATE_PATTERNS[2].search(fm_date)
                if dmy_match:
                    day, month_name, year = dmy_match.groups()
                    try:
                        parsed = datetime.strptime(f"{day} {month_name} {year}", "%d %B %Y")
                        document_date = parsed.strftime("%Y-%m-%d")
                        date_conf = 0.85
                    except ValueError:
                        document_date = fm_date
                        date_conf = 0.5
                else:
                    document_date = fm_date
                    date_conf = 0.5
    else:
        document_date, date_conf = _find_date(text)

    # Prefer frontmatter source
    fm_source = frontmatter.get("source") or frontmatter.get("author")
    if fm_source:
        source_name = fm_source
        source_conf = 0.8
    else:
        source_name, source_conf = _guess_source(text)

    # Prefer frontmatter title, then derive from body
    fm_title = frontmatter.get("title")
    if fm_title:
        canonical_title = fm_title[:200]
        title_conf = 0.9
    else:
        canonical_title, title_conf = _guess_title(text, body)

    summary, summary_conf = _summary_from_text(text, body)

    confidence = {
        "document_date": date_conf,
        "source_name": source_conf,
        "summary_one_sentence": summary_conf,
        "canonical_title": title_conf,
    }

    return ExtractedMetadata(
        document_date=document_date,
        source_name=source_name,
        audience=None,
        document_type=None,
        canonical_title=canonical_title,
        summary_one_sentence=summary,
        confidence_by_field=confidence,
    )


def extract_content(path: Path) -> ExtractedContent:
    text = extract_text(path)
    metadata = extract_metadata(text)
    return ExtractedContent(text=text, metadata=metadata)
