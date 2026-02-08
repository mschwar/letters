from __future__ import annotations

from fastapi import APIRouter

from app.core.response import envelope


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return envelope(data={"status": "ok"})
