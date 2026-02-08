from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

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
        "--target-p95-ms",
        type=float,
        default=5000.0,
        help="Target p95 latency threshold in milliseconds for pass/fail reporting.",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run grid search calibration using judged query set.",
    )
    parser.add_argument(
        "--fts-weight-values",
        type=str,
        default="0.2,0.35,0.5,0.65,0.8",
        help="Comma-separated FTS fusion weights for calibration.",
    )
    parser.add_argument(
        "--vector-weight-values",
        type=str,
        default="0.2,0.35,0.5,0.65,0.8",
        help="Comma-separated vector fusion weights for calibration.",
    )
    parser.add_argument(
        "--rrf-k-values",
        type=str,
        default="10,20,40",
        help="Comma-separated RRF k values for calibration.",
    )
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
    parser.add_argument(
        "--min-hit-rate-at-k",
        type=float,
        default=None,
        help="Optional minimum judged hit_rate_at_k threshold for gate pass.",
    )
    parser.add_argument(
        "--min-mrr",
        type=float,
        default=None,
        help="Optional minimum judged MRR threshold for gate pass.",
    )
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        default=None,
        help="Optional maximum p95 latency threshold (ms) for gate pass.",
    )
    parser.add_argument(
        "--fail-on-gate",
        action="store_true",
        help="Exit with code 1 when gate thresholds are provided and not met.",
    )
    return parser.parse_args()


def load_judged_entries(args: argparse.Namespace) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for query in args.query:
        cleaned = query.strip()
        if cleaned:
            entries.append({"query": cleaned})
    if args.queries_file:
        path = Path(args.queries_file)
        if not path.is_absolute():
            path = REPO_ROOT / path
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("query"):
                        entries.append(item)
                    elif isinstance(item, str):
                        entries.append({"query": item.strip()})
        else:
            for line in text.splitlines():
                cleaned = line.strip()
                if cleaned:
                    entries.append({"query": cleaned})
    if entries:
        return entries
    return [{"query": q} for q in DEFAULT_QUERIES]


def evaluate_one(db, entry: dict[str, Any], limit: int) -> dict:
    query = str(entry.get("query", "")).strip()
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
    archive_map = _archive_paths_for_ids(db, record["top_document_ids"])
    record["top_archive_paths"] = [archive_map.get(doc_id, "") for doc_id in record["top_document_ids"]]

    expected_suffixes = [str(x) for x in entry.get("expected_archive_suffixes", []) if str(x).strip()]
    if expected_suffixes:
        rank = _first_match_rank(record["top_archive_paths"], expected_suffixes)
        record["expected_archive_suffixes"] = expected_suffixes
        record["hit_at_k"] = rank is not None
        record["mrr"] = round(1.0 / rank, 3) if rank else 0.0

    if fallback_reason:
        record["vector_fallback_reason"] = fallback_reason
    return record


def summarize(records: list[dict]) -> dict:
    latencies = [row["latency_ms"] for row in records if "latency_ms" in row]
    avg_ms = statistics.mean(latencies) if latencies else 0.0
    p95_ms = _percentile(latencies, 95.0) if latencies else 0.0
    hybrid_count = sum(1 for row in records if row.get("retrieval_mode") == "hybrid")
    judged = [row for row in records if "hit_at_k" in row]
    hit_rate = statistics.mean([1.0 if row.get("hit_at_k") else 0.0 for row in judged]) if judged else None
    mrr = statistics.mean([float(row.get("mrr", 0.0)) for row in judged]) if judged else None
    return {
        "queries": len(records),
        "avg_latency_ms": round(avg_ms, 3),
        "p95_latency_ms": round(p95_ms, 3),
        "hybrid_count": hybrid_count,
        "judged_queries": len(judged),
        "hit_rate_at_k": round(hit_rate, 3) if hit_rate is not None else None,
        "mrr": round(mrr, 3) if mrr is not None else None,
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (percentile / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] + ((ordered[high] - ordered[low]) * weight)


def format_text(records: list[dict], totals: dict) -> str:
    lines = []
    lines.append("# Search Evaluation")
    lines.append("")
    lines.append(
        f"Queries={totals['queries']} avg_latency_ms={totals['avg_latency_ms']} "
        f"p95_latency_ms={totals['p95_latency_ms']} hybrid_count={totals['hybrid_count']} "
        f"judged={totals.get('judged_queries', 0)} hit_rate_at_k={totals.get('hit_rate_at_k')} mrr={totals.get('mrr')}"
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


def _archive_paths_for_ids(db, document_ids: list[str]) -> dict[str, str]:
    if not document_ids:
        return {}
    placeholders = ", ".join([f":id_{idx}" for idx in range(len(document_ids))])
    sql = f"SELECT id, archive_path FROM documents WHERE id IN ({placeholders})"
    params = {f"id_{idx}": value for idx, value in enumerate(document_ids)}
    rows = db.execute(search_router.text(sql), params).mappings().all()
    return {row["id"]: row.get("archive_path", "") for row in rows}


def _first_match_rank(paths: list[str], suffixes: list[str]) -> int | None:
    wanted = tuple(suffixes)
    for idx, path in enumerate(paths, start=1):
        if any(path.endswith(suffix) for suffix in wanted):
            return idx
    return None


def _parse_float_list(raw: str) -> list[float]:
    values: list[float] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        values.append(float(item))
    return values


def _parse_int_list(raw: str) -> list[int]:
    values: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        values.append(int(item))
    return values


def _score_summary(summary: dict[str, Any], target_p95_ms: float) -> float:
    hit_rate = float(summary.get("hit_rate_at_k") or 0.0)
    mrr = float(summary.get("mrr") or 0.0)
    p95 = float(summary.get("p95_latency_ms") or 0.0)
    latency_penalty = 0.0 if p95 <= target_p95_ms else min((p95 - target_p95_ms) / target_p95_ms, 1.0)
    return (hit_rate * 0.7) + (mrr * 0.3) - (latency_penalty * 0.2)


def evaluate_gate(summary: dict[str, Any], args: argparse.Namespace) -> dict[str, Any] | None:
    checks: list[dict[str, Any]] = []
    if args.min_hit_rate_at_k is not None:
        actual = float(summary.get("hit_rate_at_k") or 0.0)
        checks.append(
            {
                "name": "min_hit_rate_at_k",
                "expected": args.min_hit_rate_at_k,
                "actual": actual,
                "passed": actual >= args.min_hit_rate_at_k,
            }
        )
    if args.min_mrr is not None:
        actual = float(summary.get("mrr") or 0.0)
        checks.append(
            {
                "name": "min_mrr",
                "expected": args.min_mrr,
                "actual": actual,
                "passed": actual >= args.min_mrr,
            }
        )
    if args.max_p95_ms is not None:
        actual = float(summary.get("p95_latency_ms") or 0.0)
        checks.append(
            {
                "name": "max_p95_ms",
                "expected": args.max_p95_ms,
                "actual": actual,
                "passed": actual <= args.max_p95_ms,
            }
        )
    if not checks:
        return None
    return {
        "enabled": True,
        "passed": all(bool(check["passed"]) for check in checks),
        "checks": checks,
    }


def run_calibration(args: argparse.Namespace, entries: list[dict[str, Any]]) -> dict[str, Any]:
    fts_weights = _parse_float_list(args.fts_weight_values)
    vector_weights = _parse_float_list(args.vector_weight_values)
    k_values = _parse_int_list(args.rrf_k_values)
    if not fts_weights or not vector_weights or not k_values:
        raise SystemExit("Calibration lists cannot be empty.")

    original_settings = search_router.settings
    best: dict[str, Any] | None = None
    trials: list[dict[str, Any]] = []
    with SessionLocal() as db:
        for fts_weight in fts_weights:
            for vector_weight in vector_weights:
                for rrf_k in k_values:
                    search_router.settings = replace(
                        original_settings,
                        vector_search_enabled=True,
                        search_fusion_fts_weight=fts_weight,
                        search_fusion_vector_weight=vector_weight,
                        search_fusion_rrf_k=rrf_k,
                    )
                    records = [evaluate_one(db, entry, args.limit) for entry in entries]
                    summary = summarize(records)
                    objective = _score_summary(summary, args.target_p95_ms)
                    trial = {
                        "objective": round(objective, 4),
                        "settings": {
                            "fts_weight": fts_weight,
                            "vector_weight": vector_weight,
                            "rrf_k": rrf_k,
                        },
                        "summary": summary,
                    }
                    trials.append(trial)
                    if best is None or trial["objective"] > best["objective"]:
                        best = trial
    search_router.settings = original_settings
    return {"best": best, "trials": trials}


def main() -> None:
    args = parse_args()
    entries = load_judged_entries(args)

    original_settings = search_router.settings
    if args.vector_mode == "on":
        search_router.settings = replace(original_settings, vector_search_enabled=True)
    elif args.vector_mode == "off":
        search_router.settings = replace(original_settings, vector_search_enabled=False)

    try:
        records: list[dict] = []
        with SessionLocal() as db:
            for entry in entries:
                records.append(evaluate_one(db, entry, args.limit))
    finally:
        search_router.settings = original_settings

    totals = summarize(records)
    payload = {"summary": totals, "records": records}
    gate = evaluate_gate(totals, args)
    if gate is not None:
        payload["gate"] = gate
    if args.calibrate:
        payload["calibration"] = run_calibration(args, entries)

    exit_code = 0
    if args.fail_on_gate and gate is not None and not gate["passed"]:
        exit_code = 1

    if args.format == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(format_text(records, totals))
        if gate is not None:
            print("Gate:", "PASS" if gate["passed"] else "FAIL")
            for check in gate["checks"]:
                print(
                    f"- {check['name']}: actual={check['actual']} expected={check['expected']} "
                    f"=> {'PASS' if check['passed'] else 'FAIL'}"
                )
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
