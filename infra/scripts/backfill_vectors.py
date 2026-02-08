from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.core.config import settings  # noqa: E402
from app.services.vector_search import (  # noqa: E402
    VectorSearchUnavailable,
    create_vector_retriever,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Chroma vectors from document_fts rows.")
    parser.add_argument(
        "--db",
        type=str,
        default=str(REPO_ROOT / "data" / "db.sqlite"),
        help="Path to SQLite database.",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=settings.vector_collection,
        help="Chroma collection name.",
    )
    parser.add_argument(
        "--vector-dir",
        type=str,
        default=str(settings.vector_dir),
        help="Chroma persist directory.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional row limit for testing.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    vector_dir = Path(args.vector_dir)
    vector_dir.mkdir(parents=True, exist_ok=True)

    try:
        retriever = create_vector_retriever(
            provider=settings.vector_provider,
            persist_dir=vector_dir,
            collection_name=args.collection,
        )
    except VectorSearchUnavailable as exc:
        raise SystemExit(f"Vector backend unavailable: {exc}") from exc

    collection = getattr(retriever, "_collection", None)
    if collection is None:
        raise SystemExit("Retriever does not expose a writable collection.")

    query = (
        "SELECT document_id, COALESCE(title,''), COALESCE(summary,''), "
        "COALESCE(full_text,''), COALESCE(source_name,''), COALESCE(tags,'') FROM document_fts"
    )
    if args.limit and args.limit > 0:
        query += f" LIMIT {args.limit}"

    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(query).fetchall()
    finally:
        conn.close()

    if not rows:
        print("No document_fts rows found.")
        return

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict[str, str]] = []
    for row in rows:
        document_id, title, summary, full_text, source_name, tags = row
        ids.append(str(document_id))
        docs.append("\n".join(part for part in [title, summary, full_text] if part))
        metas.append(
            {
                "document_id": str(document_id),
                "title": str(title),
                "source_name": str(source_name),
                "tags": str(tags),
            }
        )

    collection.upsert(ids=ids, documents=docs, metadatas=metas)
    print(f"Upserted {len(ids)} vectors into collection '{args.collection}' at {vector_dir}.")


if __name__ == "__main__":
    main()

