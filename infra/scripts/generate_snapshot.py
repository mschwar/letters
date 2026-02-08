from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]

DEFAULT_DOCS = [
    "canonical-docs-v2.md",
    "README.md",
]

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "not",
    "but",
    "you",
    "your",
    "our",
    "they",
    "their",
    "them",
    "can",
    "will",
    "would",
    "should",
    "could",
    "into",
    "than",
    "then",
    "when",
    "where",
    "what",
    "which",
    "who",
    "whom",
    "how",
    "why",
    "about",
    "after",
    "before",
    "over",
    "under",
    "between",
    "within",
    "without",
    "also",
    "use",
    "using",
    "used",
    "useful",
    "todo",
}


class SnapshotWarnings:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, message: str) -> None:
        self.items.append(message)

    def as_markdown(self) -> str:
        if not self.items:
            return ""
        lines = ["## Warnings"]
        for item in self.items:
            lines.append(f"- {item}")
        return "\n".join(lines) + "\n\n"


def run_cmd(args: list[str], cwd: Path, warnings: SnapshotWarnings) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        warnings.add(f"Command not found: {' '.join(args)}")
        return ""
    if result.returncode != 0:
        stderr = result.stderr.strip()
        message = f"Command failed ({' '.join(args)}): {stderr or 'unknown error'}"
        warnings.add(message)
        return result.stdout.strip()
    return result.stdout.strip()


def safe_read_text(path: Path, warnings: SnapshotWarnings, max_chars: Optional[int] = None) -> str:
    if not path.exists():
        warnings.add(f"Missing file: {path}")
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        warnings.add(f"Failed reading {path}: {exc}")
        return ""
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n... (truncated)"
    return text


def extract_keywords(text: str, limit: int = 10) -> list[str]:
    tokens = []
    for raw in text.replace("_", " ").replace("-", " ").split():
        token = "".join(ch for ch in raw.lower() if ch.isalnum())
        if len(token) < 3:
            continue
        if token in STOPWORDS:
            continue
        tokens.append(token)
    if not tokens:
        return []
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(limit)]


def simple_gist(text: str, max_lines: int = 3, max_chars: int = 400) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    snippet = " ".join(lines[:max_lines])
    if len(snippet) > max_chars:
        return snippet[:max_chars].rstrip() + "..."
    return snippet


def ollama_gist(
    text: str,
    model: str,
    warnings: SnapshotWarnings,
    max_chars: int,
    timeout: int,
) -> str:
    if not model:
        return ""
    if not shutil.which("ollama"):
        warnings.add("Ollama requested but not installed (ollama not found in PATH).")
        return ""
    prompt = (
        "Summarize the following content in 2-3 short bullets. "
        "Focus on status, next steps, and risks.\\n\\n"
    )
    payload = (prompt + text[:max_chars]).strip()
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        warnings.add("Ollama summary timed out.")
        return ""
    if result.returncode != 0:
        warnings.add(f"Ollama summary failed: {result.stderr.strip() or 'unknown error'}")
        return ""
    return result.stdout.strip()


def build_tree(root: Path, depth: int, warnings: SnapshotWarnings) -> str:
    if depth < 0:
        return ""
    lines: list[str] = []
    ignore_dirs = {".git", "__pycache__", ".venv", "node_modules", ".mypy_cache"}

    def walk(path: Path, level: int, prefix: str) -> None:
        try:
            entries = [p for p in path.iterdir() if p.name not in ignore_dirs]
        except OSError as exc:
            warnings.add(f"Tree read failed at {path}: {exc}")
            return
        entries.sort(key=lambda p: (p.is_file(), p.name.lower()))
        total = len(entries)
        for index, entry in enumerate(entries):
            connector = "`--" if index == total - 1 else "|--"
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{connector} {entry.name}{suffix}")
            if entry.is_dir() and level > 0:
                extension = "    " if index == total - 1 else "|   "
                walk(entry, level - 1, prefix + extension)

    lines.append(root.name + "/")
    walk(root, depth, "")
    return "\n".join(lines)


def parse_git_ahead_behind(status: str) -> tuple[Optional[int], Optional[int]]:
    if not status:
        return None, None
    first_line = status.splitlines()[0]
    match = re.search(r"\[([^\]]+)\]", first_line)
    if not match:
        return None, None
    ahead: Optional[int] = None
    behind: Optional[int] = None
    for part in match.group(1).split(","):
        chunk = part.strip()
        if chunk.startswith("ahead "):
            try:
                ahead = int(chunk.split()[1])
            except (IndexError, ValueError):
                ahead = None
        elif chunk.startswith("behind "):
            try:
                behind = int(chunk.split()[1])
            except (IndexError, ValueError):
                behind = None
    return ahead, behind


def get_git_state(root: Path, warnings: SnapshotWarnings, log_count: int) -> dict[str, str]:
    state: dict[str, str] = {}
    state["branch"] = run_cmd(["git", "-C", str(root), "branch", "--show-current"], root, warnings)
    state["status"] = run_cmd(["git", "-C", str(root), "status", "-sb"], root, warnings)
    state["recent_commits"] = run_cmd(
        ["git", "-C", str(root), "log", f"-n{log_count}", "--oneline"],
        root,
        warnings,
    )
    state["diff_summary"] = run_cmd(
        ["git", "-C", str(root), "diff", "--summary"],
        root,
        warnings,
    )
    ahead, behind = parse_git_ahead_behind(state.get("status", ""))
    if ahead is not None:
        state["ahead_count"] = str(ahead)
    if behind is not None:
        state["behind_count"] = str(behind)
    if ahead and ahead > 0:
        state["push_reminder"] = f"Branch is ahead of remote by {ahead} commit(s). Run git push."
    return state


def get_pytest_summary(root: Path, warnings: SnapshotWarnings, timeout: int) -> dict[str, object]:
    venv_pytest = root / ".venv" / "bin" / "pytest"
    cmd = [str(venv_pytest), "-q"] if venv_pytest.exists() else ["pytest", "-q"]
    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        warnings.add(f"Command not found: {' '.join(cmd)}")
        return {"status": "unavailable", "returncode": None, "summary": "pytest not found"}
    except subprocess.TimeoutExpired:
        warnings.add("Pytest summary timed out.")
        return {"status": "timeout", "returncode": None, "summary": f"timeout after {timeout}s"}

    output = (result.stdout or "").strip()
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    summary = lines[-1] if lines else ("PASS" if result.returncode == 0 else "FAIL")
    status = "PASS" if result.returncode == 0 else "FAIL"
    return {
        "status": status,
        "returncode": result.returncode,
        "summary": summary,
    }


def get_db_snapshot(db_path: Path, warnings: SnapshotWarnings, limit_runs: int) -> dict[str, object]:
    if not db_path.exists():
        warnings.add(f"DB not found: {db_path}")
        return {"path": str(db_path), "exists": False}

    snapshot: dict[str, object] = {
        "path": str(db_path),
        "exists": True,
        "size_bytes": db_path.stat().st_size,
    }

    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error as exc:
        warnings.add(f"Failed to open DB {db_path}: {exc}")
        return snapshot

    try:
        cursor = conn.cursor()
        tables = cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        snapshot["tables"] = [name for name, _ in tables]
        snapshot["schema"] = [sql for _, sql in tables if sql]

        counts: dict[str, int] = {}
        for name, _ in tables:
            try:
                count = cursor.execute(f"SELECT COUNT(*) FROM {name}").fetchone()
                counts[name] = int(count[0]) if count else 0
            except sqlite3.Error:
                counts[name] = -1
        snapshot["row_counts"] = counts

        if "pipeline_runs" in snapshot.get("tables", []):
            columns = cursor.execute("PRAGMA table_info(pipeline_runs)").fetchall()
            column_names = [row[1] for row in columns]
            preferred = [
                name
                for name in [
                    "id",
                    "run_id",
                    "status",
                    "started_at",
                    "ended_at",
                    "completed_at",
                    "created_at",
                    "error_summary",
                    "document_id",
                    "ingestion_event_id",
                ]
                if name in column_names
            ]
            selected = preferred or column_names
            if selected:
                if "ended_at" in column_names and "started_at" in column_names:
                    order_expr = "COALESCE(ended_at, started_at)"
                elif "ended_at" in column_names:
                    order_expr = "ended_at"
                elif "completed_at" in column_names:
                    order_expr = "completed_at"
                elif "started_at" in column_names:
                    order_expr = "started_at"
                elif "created_at" in column_names:
                    order_expr = "created_at"
                else:
                    order_expr = "rowid"
                query = (
                    f"SELECT {', '.join(selected)} FROM pipeline_runs "
                    f"ORDER BY {order_expr} DESC LIMIT ?"
                )
                rows = cursor.execute(query, (limit_runs,)).fetchall()
                snapshot["recent_pipeline_runs"] = {
                    "columns": selected,
                    "rows": rows,
                }
            else:
                snapshot["recent_pipeline_runs"] = {"columns": [], "rows": []}
        else:
            snapshot["recent_pipeline_runs"] = {"columns": [], "rows": []}
    except sqlite3.Error as exc:
        warnings.add(f"DB query failed for {db_path}: {exc}")
    finally:
        conn.close()

    return snapshot


def format_markdown(report: dict[str, object]) -> str:
    warnings = report.get("warnings", [])
    lines = ["# LetterOps Snapshot Report", ""]
    lines.append(f"Generated: {report.get('generated_at', '')}")
    lines.append(f"Root: {report.get('root', '')}")
    lines.append("")
    if warnings:
        lines.append("## Warnings")
        for item in warnings:
            lines.append(f"- {item}")
        lines.append("")

    progress = report.get("progress")
    if isinstance(progress, dict):
        lines.append("## Progress Summary")
        content = progress.get("content", "")
        gist = progress.get("gist", "")
        if gist:
            lines.append("Gist: " + gist)
            lines.append("")
        lines.append(content.rstrip() or "(empty)")
        keywords = progress.get("keywords", [])
        if keywords:
            lines.append("")
            lines.append("Keywords: " + ", ".join(keywords))
        lines.append("")

    git_state = report.get("git")
    if isinstance(git_state, dict):
        lines.append("## Git State")
        lines.append(f"Branch: {git_state.get('branch', '')}")
        status = git_state.get("status", "")
        if status:
            lines.append("Status:")
            lines.append(status)
        reminder = git_state.get("push_reminder", "")
        if reminder:
            lines.append(f"Reminder: {reminder}")
        commits = git_state.get("recent_commits", "")
        if commits:
            lines.append("Recent commits:")
            lines.append(commits)
        diff = git_state.get("diff_summary", "")
        lines.append("Diff summary:")
        lines.append(diff or "(no diffs)")
        lines.append("")

    pytest_summary = report.get("pytest")
    if isinstance(pytest_summary, dict):
        lines.append("## Pytest Summary")
        lines.append(f"Status: {pytest_summary.get('status', 'unknown')}")
        lines.append(f"Summary: {pytest_summary.get('summary', '')}")
        lines.append("")

    docs = report.get("docs")
    if isinstance(docs, list):
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            title = doc.get("path", "Document")
            lines.append(f"## {title} Excerpt")
            excerpt = doc.get("excerpt", "")
            gist = doc.get("gist", "")
            if gist:
                lines.append("Gist: " + gist)
                lines.append("")
            lines.append(excerpt.rstrip() or "(empty)")
            keywords = doc.get("keywords", [])
            if keywords:
                lines.append("")
                lines.append("Keywords: " + ", ".join(keywords))
            lines.append("")

    db_snapshot = report.get("db")
    if isinstance(db_snapshot, dict):
        lines.append("## DB Snapshot")
        lines.append(f"Path: {db_snapshot.get('path', '')}")
        if not db_snapshot.get("exists"):
            lines.append("(missing)")
            lines.append("")
        else:
            lines.append(f"Size (bytes): {db_snapshot.get('size_bytes', '')}")
            tables = db_snapshot.get("tables", [])
            if tables:
                lines.append("Tables:")
                counts = db_snapshot.get("row_counts", {})
                for name in tables:
                    count = counts.get(name, "?")
                    lines.append(f"- {name} (rows: {count})")
            schema = db_snapshot.get("schema", [])
            if schema:
                lines.append("")
                lines.append("Schema:")
                lines.append("\n".join(schema))
            runs = db_snapshot.get("recent_pipeline_runs", {})
            if isinstance(runs, dict):
                lines.append("")
                lines.append("Recent pipeline_runs:")
                columns = runs.get("columns", [])
                rows = runs.get("rows", [])
                if columns:
                    lines.append(", ".join(columns))
                    if rows:
                        for row in rows:
                            lines.append(", ".join(str(value) for value in row))
                    else:
                        lines.append("(none)")
                else:
                    lines.append("(unavailable)")
            lines.append("")

    tree = report.get("tree")
    if isinstance(tree, str) and tree:
        lines.append("## Repo Structure")
        lines.append(tree)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_report(args: argparse.Namespace) -> dict[str, object]:
    warnings = SnapshotWarnings()
    root = ROOT_DIR

    report: dict[str, object] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(root),
    }

    progress_path = root / "progress.txt"
    progress_text = safe_read_text(progress_path, warnings, max_chars=args.progress_chars)
    progress_gist = simple_gist(progress_text, max_lines=3, max_chars=400)
    if args.ollama_model:
        progress_gist = (
            ollama_gist(
                progress_text,
                args.ollama_model,
                warnings,
                args.ollama_max_chars,
                args.ollama_timeout,
            )
            or progress_gist
        )
    report["progress"] = {
        "path": str(progress_path),
        "content": progress_text,
        "gist": progress_gist,
        "keywords": extract_keywords(progress_text),
    }

    if not args.no_git:
        report["git"] = get_git_state(root, warnings, args.git_log_count)

    if not args.no_pytest:
        report["pytest"] = get_pytest_summary(root, warnings, args.pytest_timeout)

    docs: list[dict[str, object]] = []
    for doc in args.docs:
        doc_path = root / doc
        excerpt = safe_read_text(doc_path, warnings, max_chars=args.max_doc_chars)
        doc_gist = simple_gist(excerpt, max_lines=3, max_chars=400)
        if args.ollama_model:
            doc_gist = (
                ollama_gist(
                    excerpt,
                    args.ollama_model,
                    warnings,
                    args.ollama_max_chars,
                    args.ollama_timeout,
                )
                or doc_gist
            )
        docs.append(
            {
                "path": doc,
                "excerpt": excerpt,
                "gist": doc_gist,
                "keywords": extract_keywords(excerpt),
            }
        )
    report["docs"] = docs

    if not args.no_db:
        db_path = root / args.db
        report["db"] = get_db_snapshot(db_path, warnings, args.db_runs)

    if not args.no_tree:
        if shutil.which("tree"):
            report["tree"] = run_cmd(
                ["tree", "-L", str(args.tree_depth), str(root)],
                root,
                warnings,
            )
        else:
            report["tree"] = build_tree(root, args.tree_depth, warnings)

    report["warnings"] = warnings.items
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a LetterOps snapshot report.")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="",
        help="Write report to a file instead of stdout.",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format.",
    )
    parser.add_argument(
        "--docs",
        nargs="*",
        default=DEFAULT_DOCS,
        help="Doc files to excerpt (relative to repo root).",
    )
    parser.add_argument(
        "--max-doc-chars",
        type=int,
        default=1200,
        help="Max characters per doc excerpt.",
    )
    parser.add_argument(
        "--progress-chars",
        type=int,
        default=8000,
        help="Max characters from progress.txt.",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="data/db.sqlite",
        help="SQLite DB path (relative to repo root).",
    )
    parser.add_argument(
        "--db-runs",
        type=int,
        default=5,
        help="Number of pipeline_runs rows to include.",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Skip DB snapshot.",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip git state.",
    )
    parser.add_argument(
        "--no-tree",
        action="store_true",
        help="Skip repo tree.",
    )
    parser.add_argument(
        "--no-pytest",
        action="store_true",
        help="Skip pytest summary.",
    )
    parser.add_argument(
        "--pytest-timeout",
        type=int,
        default=180,
        help="Timeout in seconds for pytest summary command.",
    )
    parser.add_argument(
        "--tree-depth",
        type=int,
        default=2,
        help="Repo tree depth.",
    )
    parser.add_argument(
        "--git-log-count",
        type=int,
        default=5,
        help="Number of recent git commits to include.",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="",
        help="Use Ollama model for gists (example: llama3).",
    )
    parser.add_argument(
        "--ollama-max-chars",
        type=int,
        default=2000,
        help="Max characters sent to Ollama per gist.",
    )
    parser.add_argument(
        "--ollama-timeout",
        type=int,
        default=30,
        help="Timeout in seconds for Ollama calls.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = generate_report(args)

    if args.format == "json":
        output = json.dumps(report, indent=2)
    else:
        output = format_markdown(report)

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = ROOT_DIR / output_path
        output_path.write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
