from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from structlog import get_logger
from sqlalchemy.orm import Session

from apps.worker.conversion import convert_text
from apps.worker.extraction import extract_content
from apps.worker.hashing import sha256_file
from apps.worker.indexing import upsert_document_fts
from apps.worker.linking import infer_links
from apps.worker.metadata_sidecar import write_metadata
from apps.worker.storage_service import build_original_path, store_original
from apps.worker.tagging import infer_tags
from apps.worker.ulid import new_ulid
from apps.worker.repos import (
    create_document,
    create_document_file,
    create_ingestion_event,
    create_metadata_version,
    create_pipeline_run,
    create_step,
    find_document_by_hash,
    upsert_document_link,
    upsert_document_tag,
    update_document_metadata,
    update_document_status,
    update_run_status,
    update_step_status,
)
from app.db.models import IngestionStatus, IngestionTrigger, RunStatus, StepStatus


logger = get_logger()


@dataclass(frozen=True)
class IngestResult:
    document_id: str
    status: RunStatus
    warnings: list[str]


def ingest_file(db: Session, path: Path) -> IngestResult:
    payload = {"path": str(path), "filename": path.name, "bytes": path.stat().st_size}
    event = create_ingestion_event(
        db, trigger_type=IngestionTrigger.manual_upload, payload=payload
    )
    run = create_pipeline_run(db, ingestion_event_id=event.id, document_id=None)
    warnings: list[str] = []

    try:
        hash_step = create_step(db, run.id, "hash", StepStatus.running)
        checksum = sha256_file(path)
        update_step_status(db, hash_step, StepStatus.success)

        dedupe_step = create_step(db, run.id, "dedupe", StepStatus.running)
        existing = find_document_by_hash(db, checksum)
        if existing:
            update_step_status(db, dedupe_step, StepStatus.success, logs="duplicate")
            run.document_id = existing.id
            update_run_status(db, run, RunStatus.success)
            event.status = IngestionStatus.processed.value
            db.add(event)
            db.commit()
            logger.info("ingest_duplicate", document_id=existing.id, sha256=checksum)
            return IngestResult(existing.id, RunStatus.success, warnings)

        update_step_status(db, dedupe_step, StepStatus.success)

        archive_step = create_step(db, run.id, "archive", StepStatus.running)
        doc_id = new_ulid()
        event_time = datetime.now(timezone.utc)
        dest_path = build_original_path(doc_id, path.name, event_time)
        stored_checksum = store_original(path, dest_path)

        document = create_document(db, doc_id, stored_checksum, str(dest_path))
        create_document_file(
            db,
            document_id=document.id,
            file_kind="original",
            path=str(dest_path),
            checksum=stored_checksum,
            bytes_size=path.stat().st_size,
        )
        update_step_status(db, archive_step, StepStatus.success)

        extract_step = create_step(db, run.id, "extract", StepStatus.running)
        extracted = extract_content(dest_path)
        metadata = extracted.metadata
        metadata_payload = {
            "document_date": metadata.document_date,
            "source_name": metadata.source_name,
            "audience": metadata.audience,
            "document_type": metadata.document_type,
            "canonical_title": metadata.canonical_title,
            "summary_one_sentence": metadata.summary_one_sentence,
            "confidence_by_field": metadata.confidence_by_field,
        }
        version_no = 1
        write_metadata(document.id, version_no, metadata_payload)
        create_metadata_version(db, document.id, version_no, metadata_payload)
        update_document_metadata(db, document.id, metadata)
        update_step_status(db, extract_step, StepStatus.success)

        convert_step = create_step(db, run.id, "convert", StepStatus.running)
        conversion = convert_text(document.id, extracted.text)
        if conversion.txt_path:
            create_document_file(
                db,
                document_id=document.id,
                file_kind="txt",
                path=str(conversion.txt_path),
                checksum=sha256_file(conversion.txt_path),
                bytes_size=conversion.txt_path.stat().st_size,
                mime_type="text/plain",
            )
        if conversion.md_path:
            create_document_file(
                db,
                document_id=document.id,
                file_kind="md",
                path=str(conversion.md_path),
                checksum=sha256_file(conversion.md_path),
                bytes_size=conversion.md_path.stat().st_size,
                mime_type="text/markdown",
            )
        if conversion.errors:
            warnings.extend(conversion.errors)
            update_step_status(db, convert_step, StepStatus.failed, logs=";".join(conversion.errors))
        else:
            update_step_status(db, convert_step, StepStatus.success)

        tag_step = create_step(db, run.id, "tag", StepStatus.running)
        tag_labels: list[str] = []
        try:
            tag_suggestions = infer_tags(db, extracted.text, metadata)
            for suggestion in tag_suggestions:
                upsert_document_tag(
                    db,
                    document_id=document.id,
                    tag_id=suggestion.tag_id,
                    confidence=suggestion.confidence,
                )
                tag_labels.append(suggestion.label)
            if tag_suggestions:
                update_step_status(db, tag_step, StepStatus.success, logs=f"tags={len(tag_suggestions)}")
            else:
                update_step_status(db, tag_step, StepStatus.skipped, logs="no tag matches")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"tagging_failed:{exc}")
            update_step_status(db, tag_step, StepStatus.failed, logs=str(exc))

        index_step = create_step(db, run.id, "index", StepStatus.running)
        tags_text = ", ".join(tag_labels) if tag_labels else None
        upsert_document_fts(
            db,
            document_id=document.id,
            title=metadata.canonical_title,
            summary=metadata.summary_one_sentence,
            full_text=extracted.text,
            source_name=metadata.source_name,
            tags=tags_text,
        )
        update_step_status(db, index_step, StepStatus.success)

        link_step = create_step(db, run.id, "link", StepStatus.running)
        try:
            link_suggestions = infer_links(db, document, metadata, extracted.text)
            for suggestion in link_suggestions:
                if suggestion.to_document_id == document.id:
                    continue
                upsert_document_link(
                    db,
                    from_document_id=document.id,
                    to_document_id=suggestion.to_document_id,
                    link_type=suggestion.link_type,
                    confidence=suggestion.confidence,
                )
            if link_suggestions:
                update_step_status(db, link_step, StepStatus.success, logs=f"links={len(link_suggestions)}")
            else:
                update_step_status(db, link_step, StepStatus.skipped, logs="no link matches")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"linking_failed:{exc}")
            update_step_status(db, link_step, StepStatus.failed, logs=str(exc))

        overall_confidence = metadata.overall_confidence()
        status = "indexed" if overall_confidence >= 0.6 else "needs_review"
        update_document_status(db, document.id, status, overall_confidence)

        run.document_id = document.id
        final_status = RunStatus.success if not warnings else RunStatus.partial_failed
        update_run_status(db, run, final_status, error=";".join(warnings) if warnings else None)
        event.status = IngestionStatus.processed.value
        db.add(event)
        db.commit()

        logger.info("ingest_success", document_id=document.id, sha256=stored_checksum)
        return IngestResult(document.id, final_status, warnings)
    except Exception as exc:  # noqa: BLE001
        update_run_status(db, run, RunStatus.failed, error=str(exc))
        event.status = IngestionStatus.failed.value
        db.add(event)
        db.commit()
        logger.exception("ingest_failed", error=str(exc))
        raise
