from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import User, UserRole
from app.main import app


def _setup_db() -> sessionmaker:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
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


def _ensure_owner_route() -> None:
    for route in app.routes:
        if getattr(route, "path", "") == "/api/v1/__test/owner-only":
            return

    router = APIRouter()

    @router.get("/api/v1/__test/owner-only")
    def owner_only(user=Depends(require_roles(UserRole.owner))):
        return {"ok": True, "user_id": user.id}

    app.include_router(router)


def test_login_and_me_roundtrip() -> None:
    client, SessionLocal = _setup_client()
    with SessionLocal() as db:
        user = User(
            id=str(uuid4()),
            email="owner@example.com",
            password_hash=hash_password("secret"),
            role="owner",
        )
        db.add(user)
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "secret"},
    )
    assert response.status_code == 200

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["data"]["user"]["email"] == "owner@example.com"
    assert body["data"]["user"]["role"] == "owner"

    app.dependency_overrides.clear()


def test_owner_only_guard() -> None:
    _ensure_owner_route()
    client, SessionLocal = _setup_client()

    with SessionLocal() as db:
        owner = User(
            id=str(uuid4()),
            email="owner2@example.com",
            password_hash=hash_password("ownerpass"),
            role="owner",
        )
        viewer = User(
            id=str(uuid4()),
            email="viewer@example.com",
            password_hash=hash_password("viewerpass"),
            role="viewer",
        )
        db.add_all([owner, viewer])
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@example.com", "password": "viewerpass"},
    )
    assert response.status_code == 200

    forbidden = client.get("/api/v1/__test/owner-only")
    assert forbidden.status_code == 403

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner2@example.com", "password": "ownerpass"},
    )
    assert response.status_code == 200

    allowed = client.get("/api/v1/__test/owner-only")
    assert allowed.status_code == 200

    app.dependency_overrides.clear()
