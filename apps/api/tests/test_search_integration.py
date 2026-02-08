from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Document, User
from app.main import app
from app.routers import search_router
from app.services.vector_search import VectorSearchUnavailable


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


def _setup_client() -> tuple[TestClient, sessionmaker]:
    SessionLocal = _setup_db()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), SessionLocal


def _seed_user_and_doc(SessionLocal: sessionmaker) -> tuple[str, str]:
    user_id = str(uuid4())
    document_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            User(
                id=user_id,
                email="viewer@example.com",
                password_hash=hash_password("secret"),
                role="viewer",
            )
        )
        db.add(
            Document(
                id=document_id,
                sha256="a" * 64,
                canonical_title="Guidance on Funds",
                source_name="Universal House of Justice",
                document_date="2026-01-01",
                summary_one_sentence="Letter describing guidance on contributions and community funds.",
                status="indexed",
                archive_path="data/archive/originals/2026/01/01/sample.md",
            )
        )
        db.execute(
            text(
                "INSERT INTO document_fts(document_id, title, summary, full_text, source_name, tags) "
                "VALUES (:document_id, :title, :summary, :full_text, :source_name, :tags)"
            ),
            {
                "document_id": document_id,
                "title": "Guidance on Funds",
                "summary": "Guidance on community funds and contributions",
                "full_text": "This letter contains guidance on funds and donations.",
                "source_name": "Universal House of Justice",
                "tags": "funds, community",
            },
        )
        db.commit()
    return user_id, document_id


def _seed_second_doc(SessionLocal: sessionmaker) -> str:
    document_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            Document(
                id=document_id,
                sha256="b" * 64,
                canonical_title="Follow-up Guidance",
                source_name="National Spiritual Assembly",
                document_date="2026-02-01",
                summary_one_sentence="Follow-up guidance touching funds and administration.",
                status="indexed",
                archive_path="data/archive/originals/2026/02/01/sample2.md",
            )
        )
        db.execute(
            text(
                "INSERT INTO document_fts(document_id, title, summary, full_text, source_name, tags) "
                "VALUES (:document_id, :title, :summary, :full_text, :source_name, :tags)"
            ),
            {
                "document_id": document_id,
                "title": "Follow-up Guidance",
                "summary": "Follow-up guidance touching funds and administration",
                "full_text": "This follow-up mentions funds and administration context.",
                "source_name": "National Spiritual Assembly",
                "tags": "funds, administration",
            },
        )
        db.commit()
    return document_id


def test_search_requires_auth() -> None:
    client, _ = _setup_client()
    response = client.post("/api/v1/search", json={"query": "funds"})
    assert response.status_code == 401
    app.dependency_overrides.clear()


def test_search_returns_ranked_results_and_answer() -> None:
    client, SessionLocal = _setup_client()
    _, document_id = _seed_user_and_doc(SessionLocal)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "secret"},
    )
    assert login.status_code == 200

    response = client.post("/api/v1/search", json={"query": "guidance on funds", "limit": 5})
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["results"]
    assert payload["data"]["results"][0]["document_id"] == document_id
    assert payload["data"]["confidence"]["label"] in {"low", "medium", "high"}
    assert 0.0 <= payload["data"]["confidence"]["score"] <= 1.0
    assert payload["data"]["citations"]
    assert payload["data"]["citations"][0]["document_id"] == document_id
    assert payload["data"]["citations"][0]["ref"] == "[1]"
    assert "[1]" in payload["data"]["answer"]
    assert payload["meta"]["retrieval_mode"] == "fts"
    app.dependency_overrides.clear()


def test_search_vector_enabled_falls_back_to_fts_when_unavailable() -> None:
    client, SessionLocal = _setup_client()
    _, document_id = _seed_user_and_doc(SessionLocal)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "secret"},
    )
    assert login.status_code == 200

    original_settings = search_router.settings
    original_factory = search_router.create_vector_retriever
    search_router.settings = replace(original_settings, vector_search_enabled=True)

    def _raise_unavailable(*args, **kwargs):
        raise VectorSearchUnavailable("vector backend unavailable")

    search_router.create_vector_retriever = _raise_unavailable
    try:
        response = client.post("/api/v1/search", json={"query": "guidance funds"})
    finally:
        search_router.settings = original_settings
        search_router.create_vector_retriever = original_factory

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["results"][0]["document_id"] == document_id
    assert payload["data"]["citations"][0]["document_id"] == document_id
    assert payload["data"]["confidence"]["label"] in {"low", "medium", "high"}
    assert payload["meta"]["retrieval_mode"] == "fts"
    assert payload["meta"]["vector_fallback_reason"] == "vector backend unavailable"
    assert payload["meta"]["result_counts"]["vector"] == 0
    app.dependency_overrides.clear()


def test_search_hybrid_fusion_prefers_vector_rank_when_configured() -> None:
    client, SessionLocal = _setup_client()
    _, doc_fts = _seed_user_and_doc(SessionLocal)
    doc_vector = _seed_second_doc(SessionLocal)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "secret"},
    )
    assert login.status_code == 200

    class _FakeRetriever:
        def search(self, query: str, limit: int):  # noqa: ARG002
            class _Hit:
                def __init__(self, document_id: str, score: float, snippet: str) -> None:
                    self.document_id = document_id
                    self.score = score
                    self.snippet = snippet

            return [
                _Hit(document_id=doc_vector, score=0.95, snippet="vector snippet A"),
                _Hit(document_id=doc_fts, score=0.70, snippet="vector snippet B"),
            ][:limit]

    original_settings = search_router.settings
    original_factory = search_router.create_vector_retriever
    search_router.settings = replace(
        original_settings,
        vector_search_enabled=True,
        search_fusion_vector_weight=1.0,
        search_fusion_fts_weight=0.0,
        search_fusion_rrf_k=10,
    )
    search_router.create_vector_retriever = lambda *args, **kwargs: _FakeRetriever()
    try:
        response = client.post("/api/v1/search", json={"query": "funds guidance", "limit": 5})
    finally:
        search_router.settings = original_settings
        search_router.create_vector_retriever = original_factory

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["retrieval_mode"] == "hybrid"
    assert payload["meta"]["result_counts"]["vector"] >= 1
    assert payload["meta"]["result_counts"]["fts"] >= 1
    assert payload["data"]["results"][0]["document_id"] == doc_vector
    assert payload["data"]["results"][0]["fusion"]["vector_rank"] == 1
    assert payload["data"]["results"][0]["fusion"]["fts_weight"] == 0.0
    app.dependency_overrides.clear()


def test_search_supports_filters_and_date_sorting() -> None:
    client, SessionLocal = _setup_client()
    _, doc_fts = _seed_user_and_doc(SessionLocal)
    doc_vector = _seed_second_doc(SessionLocal)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "secret"},
    )
    assert login.status_code == 200

    by_source = client.post(
        "/api/v1/search",
        json={
            "query": "guidance",
            "source_name": "national spiritual assembly",
            "limit": 5,
        },
    )
    assert by_source.status_code == 200
    source_payload = by_source.json()
    assert len(source_payload["data"]["results"]) == 1
    assert source_payload["data"]["results"][0]["document_id"] == doc_vector

    by_tag = client.post(
        "/api/v1/search",
        json={"query": "guidance", "tag": "community", "limit": 5},
    )
    assert by_tag.status_code == 200
    tag_payload = by_tag.json()
    assert len(tag_payload["data"]["results"]) == 1
    assert tag_payload["data"]["results"][0]["document_id"] == doc_fts

    date_sorted = client.post(
        "/api/v1/search",
        json={
            "query": "guidance",
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
            "sort_by": "date_desc",
            "limit": 5,
        },
    )
    assert date_sorted.status_code == 200
    date_payload = date_sorted.json()
    assert date_payload["meta"]["sort_by"] == "date_desc"
    assert date_payload["data"]["results"][0]["document_id"] == doc_vector
    assert date_payload["data"]["results"][1]["document_id"] == doc_fts
    app.dependency_overrides.clear()
