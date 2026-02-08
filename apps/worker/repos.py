from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Document,
    DocumentFile,
    IngestionEvent,
    IngestionStatus,
    IngestionTrigger,
    PipelineRun,
    PipelineStep,
    RunStatus,
    StepStatus,
)


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
