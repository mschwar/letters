from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.response import envelope
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.db.models import User
from app.schemas.auth import LoginRequest


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    email = payload.email
    password = payload.password

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, user.role)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_ttl_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
    )

    return envelope(data={"user_id": user.id, "role": user.role})


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return envelope(data={"status": "logged_out"})


@router.get("/me")
def me(
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    return envelope(
        data={
            "authenticated": True,
            "user": {"id": user.id, "email": user.email, "role": user.role},
        }
    )
