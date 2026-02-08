from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Document, DocumentLink, DocumentTag, Tag
from apps.worker import metadata_sidecar, storage_service, worker_config
from apps.worker.pipeline import ingest_file


SAMPLE_LETTERS: dict[str, str] = {
    "uhj_1996_funds.txt": """Subject: Guidance on community funds and contributions
January 1, 1996
Universal House of Justice

To the National Spiritual Assemblies.

This letter provides guidance on contributions to the Fund and responsibilities for community education.
""",
    "uhj_1997_funds.txt": """Subject: Guidance on community funds and contributions
1997-01-15
Universal House of Justice

This follow-up letter updates earlier guidance on contributions and community funds and expands education planning.
""",
    "nsa_1997_youth.txt": """Subject: Youth teaching plan and education schedule
March 2, 1997
National Spiritual Assembly

This letter outlines youth training, education curriculum, and community activities.
""",
    "lsa_1995_admin.txt": """Subject: Local assembly administration and committee planning
1995-11-20
Local Spiritual Assembly

This memo addresses administration, governance, and committee planning requirements.
""",
}


def _setup_db() -> sessionmaker:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE VIRTUAL TABLE document_fts USING fts5("
                "document_id UNINDEXED, title, summary, full_text, source_name, tags)"
            )
        )
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _seed_tags(SessionLocal: sessionmaker) -> None:
    tags = [
        {"key": "administration", "label": "Administration"},
        {"key": "community", "label": "Community"},
        {"key": "education", "label": "Education"},
        {"key": "funds", "label": "Funds"},
        {"key": "youth", "label": "Youth"},
    ]
    with SessionLocal() as db:
        for tag in tags:
            db.add(Tag(id=tag["key"], key=tag["key"], label=tag["label"]))
        db.commit()


def _override_worker_dirs(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    settings = worker_config.WorkerSettings(
        repo_root=tmp_path,
        data_dir=data_dir,
        archive_originals_dir=data_dir / "archive" / "originals",
        archive_derived_dir=data_dir / "archive" / "derived",
        metadata_dir=data_dir / "metadata",
        runs_dir=data_dir / "runs",
    )
    monkeypatch.setattr(worker_config, "settings", settings)
    monkeypatch.setattr(storage_service, "settings", settings)
    monkeypatch.setattr(metadata_sidecar, "settings", settings)


def _write_samples(tmp_path: Path) -> dict[str, Path]:
    sample_dir = tmp_path / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for filename, content in SAMPLE_LETTERS.items():
        path = sample_dir / filename
        path.write_text(content, encoding="utf-8")
        paths[filename] = path
    return paths


def test_ingest_samples_drive_linking(monkeypatch, tmp_path: Path) -> None:
    SessionLocal = _setup_db()
    _seed_tags(SessionLocal)
    _override_worker_dirs(tmp_path, monkeypatch)
    sample_paths = _write_samples(tmp_path)

    ingest_order = [
        "uhj_1996_funds.txt",
        "uhj_1997_funds.txt",
        "nsa_1997_youth.txt",
        "lsa_1995_admin.txt",
    ]

    doc_ids: dict[str, str] = {}
    for filename in ingest_order:
        with SessionLocal() as db:
            result = ingest_file(db, sample_paths[filename])
        doc_ids[filename] = result.document_id

    with SessionLocal() as db:
        first_doc = db.get(Document, doc_ids["uhj_1996_funds.txt"])
        assert first_doc is not None
        assert first_doc.source_name == "Universal House of Justice"
        assert first_doc.document_date == "1996-01-01"
        assert first_doc.summary_one_sentence.startswith("Subject: Guidance on community funds")

        funds_tags = db.execute(
            select(DocumentTag).where(DocumentTag.document_id == doc_ids["uhj_1996_funds.txt"])
        ).scalars().all()
        assert "funds" in {tag.tag_id for tag in funds_tags}

        supersedes_link = db.execute(
            select(DocumentLink).where(
                DocumentLink.from_document_id == doc_ids["uhj_1997_funds.txt"],
                DocumentLink.to_document_id == doc_ids["uhj_1996_funds.txt"],
            )
        ).scalar_one_or_none()
        assert supersedes_link is not None
        assert supersedes_link.link_type == "supersedes"

        nsa_links = db.execute(
            select(DocumentLink).where(
                DocumentLink.from_document_id == doc_ids["nsa_1997_youth.txt"]
            )
        ).scalars().all()
        assert not nsa_links
