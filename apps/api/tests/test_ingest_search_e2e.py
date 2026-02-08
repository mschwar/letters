from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import User
from app.main import app
from apps.worker import metadata_sidecar, storage_service, worker_config
from apps.worker.pipeline import ingest_file


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


def _setup_client(SessionLocal: sessionmaker) -> TestClient:
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


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


def test_ingest_then_search_roundtrip(monkeypatch, tmp_path: Path) -> None:
    SessionLocal = _setup_db()
    _override_worker_dirs(tmp_path, monkeypatch)

    with SessionLocal() as db:
        db.add(
            User(
                id=str(uuid4()),
                email="viewer@example.com",
                password_hash=hash_password("secret"),
                role="viewer",
            )
        )
        db.commit()

    sample_path = tmp_path / "sample_funds.txt"
    sample_path.write_text(
        """Subject: Guidance on community funds and contributions
January 1, 1996
Universal House of Justice

This letter provides guidance on contributions to the Fund and responsibilities for community education.
""",
        encoding="utf-8",
    )

    with SessionLocal() as db:
        ingest_result = ingest_file(db, sample_path)

    client = _setup_client(SessionLocal)
    try:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "secret"},
        )
        assert login.status_code == 200

        response = client.post("/api/v1/search", json={"query": "funds", "limit": 5})
        assert response.status_code == 200
        payload = response.json()
        results = payload["data"]["results"]
        assert any(item["document_id"] == ingest_result.document_id for item in results)
    finally:
        app.dependency_overrides.clear()
