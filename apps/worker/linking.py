from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Document, LinkType
from apps.worker.extraction import ExtractedMetadata


@dataclass(frozen=True)
class LinkSuggestion:
    to_document_id: str
    link_type: LinkType
    confidence: float


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", text.lower())}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _shared_tokens(a: set[str], b: set[str]) -> int:
    return len(a.intersection(b))


def infer_links(
    db: Session,
    document: Document,
    metadata: ExtractedMetadata,
    text: str,
    limit: int = 5,
) -> list[LinkSuggestion]:
    filters = []
    if metadata.source_name:
        filters.append(Document.source_name == metadata.source_name)
    if metadata.document_date:
        filters.append(Document.document_date == metadata.document_date)

    if filters:
        query = select(Document).where(Document.id != document.id, or_(*filters))
    else:
        query = (
            select(Document)
            .where(Document.id != document.id)
            .order_by(Document.created_at.desc())
            .limit(20)
        )

    candidates = db.execute(query).scalars().all()

    title_tokens = _tokens(metadata.canonical_title or "")
    summary_tokens = _tokens(metadata.summary_one_sentence or "")
    combined_tokens = title_tokens.union(summary_tokens)

    results: list[LinkSuggestion] = []
    doc_date = _parse_date(metadata.document_date)

    for candidate in candidates:
        score = 0.0
        if metadata.source_name and candidate.source_name == metadata.source_name:
            score += 0.5
        if metadata.document_date and candidate.document_date == metadata.document_date:
            score += 0.3
        if metadata.document_type and candidate.document_type == metadata.document_type:
            score += 0.1

        candidate_tokens = _tokens(
            " ".join(
                part
                for part in [
                    candidate.canonical_title,
                    candidate.summary_one_sentence,
                ]
                if part
            )
        )
        shared = _shared_tokens(combined_tokens, candidate_tokens) if combined_tokens and candidate_tokens else 0
        if shared >= 3:
            score += 0.2
        elif shared >= 1:
            score += 0.1

        if not filters and shared < 2:
            continue

        link_type = LinkType.related
        if doc_date and candidate.document_date:
            candidate_date = _parse_date(candidate.document_date)
            if candidate_date and doc_date > candidate_date and score >= 0.6:
                link_type = LinkType.supersedes
                score = min(score + 0.05, 0.95)

        if score >= 0.6:
            results.append(
                LinkSuggestion(
                    to_document_id=candidate.id,
                    link_type=link_type,
                    confidence=min(score, 0.95),
                )
            )

    results.sort(key=lambda item: item.confidence, reverse=True)
    return results[:limit]
