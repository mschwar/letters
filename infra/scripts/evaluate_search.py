from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

try:
    from app.core.database import SessionLocal  # noqa: E402
    from app.routers import search_router  # noqa: E402
    from app.services.vector_search import VectorSearchUnavailable  # noqa: E402
except ModuleNotFoundError as exc:  # pragma: no cover - runtime environment guard
    missing = getattr(exc, "name", "dependency")
    print(
        f"Missing dependency: {missing}. Run with project venv, e.g. "
        f"`.venv/bin/python infra/scripts/evaluate_search.py`.",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc


DEFAULT_QUERIES = [
    "guidance on funds",
    "community education",
    "administration policy",
    "youth training",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate LetterOps retrieval quality + latency.")
    parser.add_argument("--query", action="append", default=[], help="Query to evaluate (repeatable).")
    parser.add_argument(
        "--queries-file",
        type=str,
        default="",
        help="Path to JSON array or newline-delimited text file with queries.",
    )
    parser.add_argument("--limit", type=int, default=5, help="Results per query.")
    parser.add_argument(
        "--vector-mode",
        choices=["auto", "on", "off"],
        default="auto",
        help="Force vector feature flag on/off, or keep current setting (auto).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format.",
    )
    return parser.parse_args()


def load_queries(args: argparse.Namespace) -> list[str]:
    queries = list(args.query)
    if args.queries_file:
        path = Path(args.queries_file)
        if not path.is_absolute():
            path = REPO_ROOT / path
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            data = json.loads(text)
            if isinstance(data, list):
                queries.extend(str(item).strip() for item in data)
        else:
            queries.extend(line.strip() for line in text.splitlines())
    cleaned = [q for q in queries if q]
    return cleaned or list(DEFAULT_QUERIES)


def evaluate_one(db, query: str, limit: int) -> dict:
    match_query = search_router._build_fts_query(query)
    if not match_query:
        return {
            "query": query,
            "error": "no alphanumeric tokens",
            "retrieval_mode": "none",
            "latency_ms": 0.0,
            "result_count": 0,
            "top_document_ids": [],
        }

    started = time.perf_counter()
    fts_results = search_router._query_fts(db, match_query, limit)
    vector_results: list[dict] = []
    retrieval_mode = "fts"
    fallback_reason: str | None = None

    if search_router.settings.vector_search_enabled:
        try:
            vector_results = search_router._query_vector(db, query, limit)
            if vector_results and fts_results:
                retrieval_mode = "hybrid"
            elif vector_results:
                retrieval_mode = "vector"
        except VectorSearchUnavailable as exc:
            fallback_reason = str(exc)

    results = search_router._fuse_results(fts_results, vector_results, limit)
    confidence_score, confidence_label = search_router._confidence_from_results(results)
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    record = {
        "query": query,
        "retrieval_mode": retrieval_mode,
        "latency_ms": round(elapsed_ms, 3),
        "result_count": len(results),
        "result_counts": {"fts": len(fts_results), "vector": len(vector_results)},
        "confidence": {"score": confidence_score, "label": confidence_label},
        "top_document_ids": [item["document_id"] for item in results[:3]],
    }
    if fallback_reason:
        record["vector_fallback_reason"] = fallback_reason
    return record


def summarize(records: list[dict]) -> dict:
    latencies = [row["latency_ms"] for row in records if "latency_ms" in row]
    avg_ms = statistics.mean(latencies) if latencies else 0.0
    p95_ms = sorted(latencies)[max(int(len(latencies) * 0.95) - 1, 0)] if latencies else 0.0
    hybrid_count = sum(1 for row in records if row.get("retrieval_mode") == "hybrid")
    return {
        "queries": len(records),
        "avg_latency_ms": round(avg_ms, 3),
        "p95_latency_ms": round(p95_ms, 3),
        "hybrid_count": hybrid_count,
    }


def format_text(records: list[dict], totals: dict) -> str:
    lines = []
    lines.append("# Search Evaluation")
    lines.append("")
    lines.append(
        f"Queries={totals['queries']} avg_latency_ms={totals['avg_latency_ms']} "
        f"p95_latency_ms={totals['p95_latency_ms']} hybrid_count={totals['hybrid_count']}"
    )
    lines.append("")
    lines.append("query | mode | latency_ms | fts/vector | confidence | top_ids")
    lines.append("--- | --- | ---: | --- | --- | ---")
    for row in records:
        counts = row.get("result_counts", {})
        lines.append(
            f"{row['query']} | {row.get('retrieval_mode', 'n/a')} | {row.get('latency_ms', 0.0)} | "
            f"{counts.get('fts', 0)}/{counts.get('vector', 0)} | "
            f"{row.get('confidence', {}).get('label', 'n/a')} "
            f"({row.get('confidence', {}).get('score', 0.0)}) | "
            f"{', '.join(row.get('top_document_ids', []))}"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    queries = load_queries(args)

    original_settings = search_router.settings
    if args.vector_mode == "on":
        search_router.settings = replace(original_settings, vector_search_enabled=True)
    elif args.vector_mode == "off":
        search_router.settings = replace(original_settings, vector_search_enabled=False)

    try:
        records: list[dict] = []
        with SessionLocal() as db:
            for query in queries:
                records.append(evaluate_one(db, query, args.limit))
    finally:
        search_router.settings = original_settings

    totals = summarize(records)
    payload = {"summary": totals, "records": records}
    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(format_text(records, totals))


if __name__ == "__main__":
    main()
