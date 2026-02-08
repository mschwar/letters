from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select
from structlog import get_logger

from apps.worker.db_session import SessionLocal
from apps.worker.extraction import extract_text, ExtractedMetadata
from apps.worker.indexing import upsert_document_fts
from apps.worker.linking import infer_links
from apps.worker.repos import (
    upsert_document_link,
    upsert_document_tag,
)
from apps.worker.tagging import infer_tags
from app.db.models import Document, DocumentFile
from app.core.logging import configure_logging


logger = get_logger()


def _load_text(db, document: Document) -> str | None:
    file = (
        db.execute(
            select(DocumentFile)
            .where(
                DocumentFile.document_id == document.id,
                DocumentFile.file_kind.in_(["md", "txt"]),
            )
            .order_by(DocumentFile.file_kind.desc())
        )
        .scalars()
        .first()
    )
    if file and Path(file.path).exists():
        return extract_text(Path(file.path))
    if document.archive_path and Path(document.archive_path).exists():
        return extract_text(Path(document.archive_path))
    return None


def _metadata_from_document(document: Document) -> ExtractedMetadata:
    return ExtractedMetadata(
        document_date=document.document_date,
        source_name=document.source_name,
        audience=document.audience,
        document_type=document.document_type,
        canonical_title=document.canonical_title,
        summary_one_sentence=document.summary_one_sentence,
        confidence_by_field={},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill tags and links for existing documents.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of documents")
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()

    with SessionLocal() as db:
        query = select(Document).order_by(Document.created_at.desc())
        if args.limit:
            query = query.limit(args.limit)
        documents = db.execute(query).scalars().all()

        tags_added = 0
        links_added = 0
        docs_processed = 0
        warnings: list[str] = []

        for document in documents:
            docs_processed += 1
            text = _load_text(db, document)
            if not text:
                warnings.append(f"missing_text:{document.id}")
                continue

            metadata = _metadata_from_document(document)

            tag_suggestions = infer_tags(db, text, metadata)
            for suggestion in tag_suggestions:
                upsert_document_tag(
                    db,
                    document_id=document.id,
                    tag_id=suggestion.tag_id,
                    confidence=suggestion.confidence,
                )
                tags_added += 1

            link_suggestions = infer_links(db, document, metadata, text)
            for suggestion in link_suggestions:
                upsert_document_link(
                    db,
                    from_document_id=document.id,
                    to_document_id=suggestion.to_document_id,
                    link_type=suggestion.link_type,
                    confidence=suggestion.confidence,
                )
                links_added += 1

            tags_text = ", ".join([tag.label for tag in tag_suggestions]) if tag_suggestions else None
            upsert_document_fts(
                db,
                document_id=document.id,
                title=document.canonical_title,
                summary=document.summary_one_sentence,
                full_text=text,
                source_name=document.source_name,
                tags=tags_text,
            )

        logger.info(
            "backfill_complete",
            documents=docs_processed,
            tags_added=tags_added,
            links_added=links_added,
            warnings=warnings,
        )


if __name__ == "__main__":
    main()
