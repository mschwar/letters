from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from apps.worker.extraction import ExtractedMetadata
from apps.worker.repos import list_tag_aliases, list_tags


@dataclass(frozen=True)
class TagSuggestion:
    tag_id: str
    label: str
    confidence: float


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _term_pattern(term: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in term.lower().split() if part]
    if not parts:
        return re.compile(r"a^")
    pattern = r"\b" + r"\s+".join(parts) + r"\b"
    return re.compile(pattern)


def _score_match(term: str, header_text: str, body_text: str) -> float:
    pattern = _term_pattern(term)
    if pattern.search(header_text):
        return 0.85
    if pattern.search(body_text):
        return 0.65
    return 0.0


KEYWORD_HINTS: dict[str, list[str]] = {
    "administration": [
        "administration",
        "governance",
        "policy",
        "committee",
        "council",
        "planning",
        "strategy",
        "requirements",
        "prd",
    ],
    "community": [
        "community",
        "assembly",
        "local spiritual assembly",
        "national spiritual assembly",
        "community building",
    ],
    "education": [
        "education",
        "teaching",
        "training",
        "school",
        "study",
        "curriculum",
    ],
    "funds": [
        "fund",
        "funds",
        "donation",
        "contribution",
        "budget",
        "finance",
    ],
    "youth": [
        "youth",
        "young",
        "junior",
        "student",
        "children",
    ],
}


def infer_tags(db: Session, text: str, metadata: ExtractedMetadata) -> list[TagSuggestion]:
    tags = list_tags(db)
    aliases = list_tag_aliases(db)
    if not tags:
        return []

    alias_map: dict[str, list[str]] = {}
    for alias in aliases:
        alias_map.setdefault(alias.tag_id, []).append(alias.alias)

    header_text = _normalize(
        " ".join(
            part
            for part in [
                metadata.canonical_title,
                metadata.summary_one_sentence,
                metadata.document_type,
                metadata.audience,
                metadata.source_name,
            ]
            if part
        )
    )
    body_text = _normalize(text)

    suggestions: list[TagSuggestion] = []
    for tag in tags:
        terms = [tag.key, tag.label]
        terms.extend(alias_map.get(tag.id, []))
        terms.extend(KEYWORD_HINTS.get(tag.key, []))
        best = 0.0
        for term in terms:
            if not term:
                continue
            best = max(best, _score_match(term, header_text, body_text))
        if best >= 0.6:
            suggestions.append(TagSuggestion(tag_id=tag.id, label=tag.label, confidence=best))

    suggestions.sort(key=lambda item: item.confidence, reverse=True)
    return suggestions


def tags_to_text(tags: Iterable[TagSuggestion]) -> str:
    labels = [tag.label for tag in tags]
    return ", ".join(labels)
