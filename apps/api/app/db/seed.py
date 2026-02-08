from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.db.models import Tag, User


DEFAULT_TAGS = [
    {"key": "administration", "label": "Administration"},
    {"key": "community", "label": "Community"},
    {"key": "education", "label": "Education"},
    {"key": "funds", "label": "Funds"},
    {"key": "youth", "label": "Youth"},
]


def load_seed_tags(seed_path: Path) -> list[dict[str, str]]:
    if seed_path.exists():
        with seed_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return [tag for tag in data if "key" in tag and "label" in tag]
    return DEFAULT_TAGS


def seed_defaults(db: Session, settings: Settings) -> dict[str, int]:
    created_users = 0
    created_tags = 0

    if settings.owner_email and settings.owner_password:
        existing_user = db.execute(
            select(User).where(User.email == settings.owner_email)
        ).scalar_one_or_none()
        if existing_user is None:
            user = User(
                id=str(uuid4()),
                email=settings.owner_email,
                password_hash=hash_password(settings.owner_password),
                role="owner",
            )
            db.add(user)
            created_users += 1

    tags = load_seed_tags(settings.seed_tags_path)
    for tag in tags:
        existing_tag = db.execute(select(Tag).where(Tag.key == tag["key"])).scalar_one_or_none()
        if existing_tag is None:
            db.add(
                Tag(
                    id=tag["key"],
                    key=tag["key"],
                    label=tag["label"],
                )
            )
            created_tags += 1

    if created_users or created_tags:
        db.commit()
    return {"users": created_users, "tags": created_tags}
