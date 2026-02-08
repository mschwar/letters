from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from structlog import get_logger

from apps.worker.db_session import SessionLocal
from apps.worker.hashing import sha256_file
from apps.worker.storage_service import build_original_path, store_original
from apps.worker.ulid import new_ulid
from apps.worker.repos import (
    create_document,
    create_document_file,
    create_ingestion_event,
    create_pipeline_run,
    create_step,
    find_document_by_hash,
    update_run_status,
    update_step_status,
)
from app.core.logging import configure_logging
from app.db.models import IngestionStatus, IngestionTrigger, RunStatus, StepStatus


logger = get_logger()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a single file into LetterOps.")
    parser.add_argument("path", help="Path to the file to ingest")
    return parser.parse_args()


def ingest(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")

    with SessionLocal() as db:
        payload = {"path": str(path), "filename": path.name, "bytes": path.stat().st_size}
        event = create_ingestion_event(
            db, trigger_type=IngestionTrigger.manual_upload, payload=payload
        )
        run = create_pipeline_run(db, ingestion_event_id=event.id, document_id=None)

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
                return

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

            run.document_id = document.id
            update_run_status(db, run, RunStatus.success)
            event.status = IngestionStatus.processed.value
            db.add(event)
            db.commit()

            logger.info("ingest_success", document_id=document.id, sha256=stored_checksum)
        except Exception as exc:  # noqa: BLE001
            update_run_status(db, run, RunStatus.failed, error=str(exc))
            event.status = IngestionStatus.failed.value
            db.add(event)
            db.commit()
            logger.exception("ingest_failed", error=str(exc))
            raise


def main() -> None:
    configure_logging()
    args = parse_args()
    ingest(Path(args.path))


if __name__ == "__main__":
    main()
