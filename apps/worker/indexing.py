from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upsert_document_fts(
    db: Session,
    document_id: str,
    title: str | None,
    summary: str | None,
    full_text: str | None,
    source_name: str | None,
    tags: str | None,
) -> None:
    db.execute(
        text(
            "DELETE FROM document_fts WHERE document_id = :document_id"
        ),
        {"document_id": document_id},
    )
    db.execute(
        text(
            "INSERT INTO document_fts(document_id, title, summary, full_text, source_name, tags) "
            "VALUES (:document_id, :title, :summary, :full_text, :source_name, :tags)"
        ),
        {
            "document_id": document_id,
            "title": title,
            "summary": summary,
            "full_text": full_text,
            "source_name": source_name,
            "tags": tags,
        },
    )
    db.commit()
