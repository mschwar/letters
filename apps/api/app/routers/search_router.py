from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_viewer
from app.core.response import envelope
from app.db.models import User
from app.schemas.search import SearchRequest


router = APIRouter(prefix="/search", tags=["search"])


def _build_fts_query(raw_query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]{2,}", raw_query.lower())
    # Prefix matching keeps natural language queries forgiving for partial terms.
    return " AND ".join(f"{token}*" for token in tokens[:12])


@router.post("")
def search_documents(
    payload: SearchRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_viewer)],
) -> dict:
    match_query = _build_fts_query(payload.query)
    if not match_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query must contain at least one alphanumeric token",
        )

    sql = text(
        """
        SELECT
            f.document_id AS document_id,
            COALESCE(d.canonical_title, '') AS title,
            COALESCE(d.source_name, '') AS source_name,
            COALESCE(d.document_date, '') AS document_date,
            COALESCE(d.summary_one_sentence, '') AS summary,
            snippet(document_fts, 3, '[', ']', '...', 20) AS snippet,
            bm25(document_fts) AS rank_score
        FROM document_fts AS f
        JOIN documents AS d ON d.id = f.document_id
        WHERE document_fts MATCH :match_query
        ORDER BY rank_score
        LIMIT :limit
        """
    )

    try:
        rows = db.execute(sql, {"match_query": match_query, "limit": payload.limit}).mappings().all()
    except SQLAlchemyError as exc:
        message = str(getattr(exc, "orig", exc))
        if "no such table: document_fts" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search index unavailable; run migrations and reindex",
            ) from exc
        raise

    results = [
        {
            "document_id": row["document_id"],
            "title": row["title"],
            "source_name": row["source_name"],
            "document_date": row["document_date"],
            "summary": row["summary"],
            "snippet": row["snippet"],
            "score": abs(float(row["rank_score"])) if row["rank_score"] is not None else 0.0,
        }
        for row in rows
    ]

    if results:
        top = results[:3]
        citations = ", ".join(item["document_id"] for item in top)
        answer = f"Found {len(results)} relevant documents. Top sources: {citations}."
    else:
        answer = "No matching documents found."

    return envelope(
        data={
            "query": payload.query,
            "answer": answer,
            "results": results,
        },
        meta={"retrieval_mode": "fts", "request_user_id": user.id},
    )

