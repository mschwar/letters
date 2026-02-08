from __future__ import annotations

import argparse
from pathlib import Path

from structlog import get_logger

from apps.worker.db_session import SessionLocal
from apps.worker.pipeline import ingest_file
from app.core.logging import configure_logging


logger = get_logger()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a single file into LetterOps.")
    parser.add_argument("path", help="Path to the file to ingest")
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    with SessionLocal() as db:
        ingest_file(db, Path(args.path))


if __name__ == "__main__":
    main()
