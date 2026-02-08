from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
API_DIR = ROOT_DIR / "apps" / "api"
sys.path.append(str(API_DIR))

from app.core.config import settings  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.db.seed import seed_defaults  # noqa: E402


configure_logging()
logger = get_logger()


def main() -> None:
    with SessionLocal() as db:
        result = seed_defaults(db, settings)
    logger.info("seed_defaults_complete", **result)


if __name__ == "__main__":
    main()
