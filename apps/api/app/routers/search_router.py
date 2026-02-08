from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text, bindparam
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_viewer
from app.core.response import envelope
from app.db.models import User
from app.schemas.search import SearchRequest
from app.services.vector_search import VectorSearchUnavailable, create_vector_retriever


router = APIRouter(prefix="/search", tags=["search"])


def _build_fts_query(raw_query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]{2,}", raw_query.lower())
    # Prefix matching keeps natural language queries forgiving for partial terms.
    return " AND ".join(f"{token}*" for token in tokens[:12])


def _query_fts(db: Session, match_query: str, limit: int) -> list[dict]:
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
    rows = db.execute(sql, {"match_query": match_query, "limit": limit}).mappings().all()
    return [
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


def _query_docs_by_ids(db: Session, document_ids: list[str]) -> dict[str, dict]:
    if not document_ids:
        return {}
    sql = (
        text(
            """
            SELECT
                id AS document_id,
                COALESCE(canonical_title, '') AS title,
                COALESCE(source_name, '') AS source_name,
                COALESCE(document_date, '') AS document_date,
                COALESCE(summary_one_sentence, '') AS summary
            FROM documents
            WHERE id IN :document_ids
            """
        )
        .bindparams(bindparam("document_ids", expanding=True))
    )
    rows = db.execute(sql, {"document_ids": document_ids}).mappings().all()
    return {
        row["document_id"]: {
            "document_id": row["document_id"],
            "title": row["title"],
            "source_name": row["source_name"],
            "document_date": row["document_date"],
            "summary": row["summary"],
        }
        for row in rows
    }


def _query_vector(db: Session, query: str, limit: int) -> list[dict]:
    retriever = create_vector_retriever(
        provider=settings.vector_provider,
        persist_dir=settings.vector_dir,
        collection_name=settings.vector_collection,
    )
    hits = retriever.search(query=query, limit=limit)
    docs = _query_docs_by_ids(db, [hit.document_id for hit in hits])

    results: list[dict] = []
    for hit in hits:
        doc = docs.get(hit.document_id)
        if not doc:
            continue
        results.append(
            {
                **doc,
                "snippet": hit.snippet or doc["summary"],
                "score": hit.score,
            }
        )
    return results


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

    retrieval_mode = "fts"
    vector_fallback_reason: str | None = None
    try:
        if settings.vector_search_enabled:
            results = _query_vector(db, payload.query, payload.limit)
            if results:
                retrieval_mode = "vector"
            else:
                results = _query_fts(db, match_query, payload.limit)
        else:
            results = _query_fts(db, match_query, payload.limit)
    except VectorSearchUnavailable as exc:
        vector_fallback_reason = str(exc)
        results = _query_fts(db, match_query, payload.limit)
    except SQLAlchemyError as exc:
        message = str(getattr(exc, "orig", exc))
        if "no such table: document_fts" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Search index unavailable; run migrations and reindex",
            ) from exc
        raise

    if results:
        top = results[:3]
        citations = ", ".join(item["document_id"] for item in top)
        answer = f"Found {len(results)} relevant documents. Top sources: {citations}."
    else:
        answer = "No matching documents found."

    meta = {"retrieval_mode": retrieval_mode, "request_user_id": user.id}
    if vector_fallback_reason:
        meta["vector_fallback_reason"] = vector_fallback_reason

    return envelope(
        data={
            "query": payload.query,
            "answer": answer,
            "results": results,
        },
        meta=meta,
    )
