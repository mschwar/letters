from __future__ import annotations

import sys
from pathlib import Path

# Ensure apps/api is on sys.path for shared models
REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "apps" / "api"
sys.path.append(str(API_DIR))

from app.core.database import SessionLocal  # noqa: E402

__all__ = ["SessionLocal"]
