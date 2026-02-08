from __future__ import annotations

import warnings
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_ttl_minutes
    )
    payload = {"sub": subject, "role": role, "type": "access", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)
    payload = {"sub": subject, "role": role, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    # python-jose uses datetime.utcnow() internally during decode on some versions.
    # Suppress only that deprecation warning until upstream releases a fix.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*datetime\.datetime\.utcnow\(\) is deprecated.*",
            category=DeprecationWarning,
            module=r"jose\.jwt",
        )
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
