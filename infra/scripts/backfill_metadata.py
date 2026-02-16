"""Re-extract metadata for all documents using the improved extraction pipeline.

Usage:
    python infra/scripts/backfill_metadata.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from apps.worker.extraction import extract_content  # noqa: E402
from apps.worker.indexing import upsert_document_fts  # noqa: E402


def backfill(dry_run: bool = False) -> None:
    db = SessionLocal()
    rows = db.execute(
        text("SELECT id, archive_path FROM documents ORDER BY id")
    ).mappings().all()

    updated = 0
    skipped = 0
    errors = 0

    for row in rows:
        doc_id = row["id"]
        archive_path = Path(row["archive_path"])

        if not archive_path.exists():
            print(f"  SKIP {doc_id}: file not found at {archive_path}")
            skipped += 1
            continue

        try:
            result = extract_content(archive_path)
            meta = result.metadata
            confidence = meta.overall_confidence()
            status = "indexed" if confidence >= 0.6 else "needs_review"

            title_display = (meta.canonical_title or "(none)")[:60]
            date_display = meta.document_date or "(none)"

            if dry_run:
                print(f"  DRY  {doc_id}: title={title_display!r} date={date_display} conf={confidence:.2f}")
            else:
                db.execute(
                    text(
                        "UPDATE documents SET "
                        "canonical_title=:title, source_name=:source, "
                        "document_date=:date, summary_one_sentence=:summary, "
                        "confidence_overall=:confidence, status=:status "
                        "WHERE id=:doc_id"
                    ),
                    {
                        "title": meta.canonical_title,
                        "source": meta.source_name,
                        "date": meta.document_date,
                        "summary": meta.summary_one_sentence,
                        "confidence": confidence,
                        "status": status,
                        "doc_id": doc_id,
                    },
                )

                # Also update FTS index with new title
                upsert_document_fts(
                    db,
                    document_id=doc_id,
                    title=meta.canonical_title,
                    summary=meta.summary_one_sentence,
                    full_text=result.text,
                    source_name=meta.source_name,
                    tags=None,  # preserve existing tags by not clearing
                )

                print(f"  OK   {doc_id}: title={title_display!r} date={date_display} conf={confidence:.2f} -> {status}")
            updated += 1
        except Exception as exc:
            print(f"  ERR  {doc_id}: {exc}")
            errors += 1

    if not dry_run:
        db.commit()
    db.close()

    print(f"\nDone: {updated} updated, {skipped} skipped, {errors} errors (dry_run={dry_run})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill document metadata")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)
