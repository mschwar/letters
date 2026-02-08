from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    DocumentFile,
    DocumentLink,
    DocumentMetadataVersion,
    DocumentTag,
    IngestionEvent,
    IngestionStatus,
    IngestionTrigger,
    LinkCreatedBy,
    LinkState,
    LinkType,
    PipelineRun,
    PipelineStep,
    RunStatus,
    StepStatus,
    Tag,
    TagAlias,
    TagAssignedBy,
)
from apps.worker.extraction import ExtractedMetadata


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_ingestion_event(
    db: Session,
    trigger_type: IngestionTrigger,
    payload: dict,
    source_id: str | None = None,
    status: IngestionStatus = IngestionStatus.received,
) -> IngestionEvent:
    event = IngestionEvent(
        id=str(uuid4()),
        source_id=source_id,
        trigger_type=trigger_type.value,
        payload_json=json.dumps(payload),
        event_time=now_iso(),
        status=status.value,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def create_pipeline_run(db: Session, ingestion_event_id: str, document_id: str | None) -> PipelineRun:
    run = PipelineRun(
        id=str(uuid4()),
        ingestion_event_id=ingestion_event_id,
        document_id=document_id,
        status=RunStatus.running.value,
        started_at=now_iso(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def update_run_status(db: Session, run: PipelineRun, status: RunStatus, error: str | None = None) -> None:
    run.status = status.value
    run.ended_at = now_iso()
    run.error_summary = error
    db.add(run)
    db.commit()


def create_step(db: Session, run_id: str, step_name: str, status: StepStatus) -> PipelineStep:
    step = PipelineStep(
        id=str(uuid4()),
        run_id=run_id,
        step_name=step_name,
        status=status.value,
        started_at=now_iso(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def update_step_status(db: Session, step: PipelineStep, status: StepStatus, logs: str | None = None) -> None:
    step.status = status.value
    step.ended_at = now_iso()
    step.logs = logs
    db.add(step)
    db.commit()


def find_document_by_hash(db: Session, sha256: str) -> Document | None:
    return db.execute(select(Document).where(Document.sha256 == sha256)).scalar_one_or_none()


def create_document(
    db: Session,
    doc_id: str,
    sha256: str,
    archive_path: str,
) -> Document:
    document = Document(
        id=doc_id,
        sha256=sha256,
        status="ingested",
        archive_path=archive_path,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def update_document_metadata(db: Session, document_id: str, metadata: ExtractedMetadata) -> None:
    db.execute(
        text(
            "UPDATE documents SET canonical_title=:canonical_title, source_name=:source_name, "
            "audience=:audience, document_date=:document_date, document_type=:document_type, "
            "summary_one_sentence=:summary_one_sentence WHERE id=:document_id"
        ),
        {
            "canonical_title": metadata.canonical_title,
            "source_name": metadata.source_name,
            "audience": metadata.audience,
            "document_date": metadata.document_date,
            "document_type": metadata.document_type,
            "summary_one_sentence": metadata.summary_one_sentence,
            "document_id": document_id,
        },
    )
    db.commit()


def update_document_status(db: Session, document_id: str, status: str, confidence: float) -> None:
    db.execute(
        text(
            "UPDATE documents SET status=:status, confidence_overall=:confidence_overall WHERE id=:document_id"
        ),
        {
            "status": status,
            "confidence_overall": confidence,
            "document_id": document_id,
        },
    )
    db.commit()


def create_metadata_version(
    db: Session, document_id: str, version_no: int, metadata_payload: dict
) -> DocumentMetadataVersion:
    version = DocumentMetadataVersion(
        id=str(uuid4()),
        document_id=document_id,
        version_no=version_no,
        metadata_json=json.dumps(metadata_payload),
        edited_by_user_id=None,
        edit_reason="auto",
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def create_document_file(
    db: Session,
    document_id: str,
    file_kind: str,
    path: str,
    checksum: str,
    bytes_size: int | None,
    mime_type: str | None = None,
) -> DocumentFile:
    doc_file = DocumentFile(
        id=str(uuid4()),
        document_id=document_id,
        file_kind=file_kind,
        path=path,
        mime_type=mime_type,
        bytes=bytes_size,
        checksum_sha256=checksum,
    )
    db.add(doc_file)
    db.commit()
    db.refresh(doc_file)
    return doc_file


def list_tags(db: Session) -> list[Tag]:
    return db.execute(select(Tag).where(Tag.is_active == 1)).scalars().all()


def list_tag_aliases(db: Session) -> list[TagAlias]:
    return db.execute(select(TagAlias)).scalars().all()


def upsert_document_tag(
    db: Session,
    document_id: str,
    tag_id: str,
    confidence: float,
    assigned_by: TagAssignedBy = TagAssignedBy.system,
) -> DocumentTag:
    existing = db.execute(
        select(DocumentTag).where(
            DocumentTag.document_id == document_id,
            DocumentTag.tag_id == tag_id,
        )
    ).scalar_one_or_none()
    if existing:
        if confidence > existing.confidence:
            existing.confidence = confidence
            db.add(existing)
            db.commit()
        return existing
    record = DocumentTag(
        document_id=document_id,
        tag_id=tag_id,
        confidence=confidence,
        assigned_by=assigned_by.value,
    )
    db.add(record)
    db.commit()
    return record


def upsert_document_link(
    db: Session,
    from_document_id: str,
    to_document_id: str,
    link_type: LinkType = LinkType.related,
    confidence: float = 0.6,
    state: LinkState = LinkState.suggested,
    created_by: LinkCreatedBy = LinkCreatedBy.system,
) -> DocumentLink:
    existing = db.execute(
        select(DocumentLink).where(
            DocumentLink.from_document_id == from_document_id,
            DocumentLink.to_document_id == to_document_id,
            DocumentLink.link_type == link_type.value,
        )
    ).scalar_one_or_none()
    if existing:
        if confidence > existing.confidence:
            existing.confidence = confidence
            db.add(existing)
            db.commit()
        return existing
    link = DocumentLink(
        id=str(uuid4()),
        from_document_id=from_document_id,
        to_document_id=to_document_id,
        link_type=link_type.value,
        confidence=confidence,
        state=state.value,
        created_by=created_by.value,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link
