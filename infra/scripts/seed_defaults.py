from __future__ import annotations

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.database import SessionLocal
from app.db.seed import seed_defaults


configure_logging()
logger = get_logger()


def main() -> None:
    with SessionLocal() as db:
        result = seed_defaults(db, settings)
    logger.info("seed_defaults_complete", **result)


if __name__ == "__main__":
    main()
