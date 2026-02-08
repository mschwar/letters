from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class VectorSearchUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class VectorHit:
    document_id: str
    score: float
    snippet: str


class ChromaVectorRetriever:
    def __init__(self, persist_dir: Path, collection_name: str) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise VectorSearchUnavailable("chromadb is not installed") from exc

        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(name=collection_name)

    def search(self, query: str, limit: int) -> list[VectorHit]:
        try:
            response = self._collection.query(
                query_texts=[query],
                n_results=limit,
                include=["distances", "documents", "metadatas"],
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorSearchUnavailable(f"vector query failed: {exc}") from exc

        ids = _first_list(response.get("ids"))
        distances = _first_list(response.get("distances"))
        documents = _first_list(response.get("documents"))
        metadatas = _first_list(response.get("metadatas"))

        hits: list[VectorHit] = []
        for idx, raw_id in enumerate(ids):
            metadata = metadatas[idx] if idx < len(metadatas) and isinstance(metadatas[idx], dict) else {}
            document_id = str(metadata.get("document_id") or raw_id)
            distance = _to_float(distances[idx]) if idx < len(distances) else 1.0
            score = 1.0 / (1.0 + max(distance, 0.0))
            snippet = str(documents[idx])[:280] if idx < len(documents) and documents[idx] else ""
            hits.append(VectorHit(document_id=document_id, score=score, snippet=snippet))
        return hits


def create_vector_retriever(provider: str, persist_dir: Path, collection_name: str) -> Any:
    normalized = provider.lower().strip()
    if normalized == "chroma":
        return ChromaVectorRetriever(persist_dir=persist_dir, collection_name=collection_name)
    raise VectorSearchUnavailable(f"unsupported vector provider: {provider}")


def _first_list(value: Any) -> list[Any]:
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value[0]
    if isinstance(value, list):
        return value
    return []


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 1.0

