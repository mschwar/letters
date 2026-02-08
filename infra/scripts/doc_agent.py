#!/usr/bin/env python3
"""Doc Agent: keep docs aligned with code changes."""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
DOC_FILES = [
    "BACKEND_STRUCTURE.md",
    "IMPLEMENTATION_PLAN.md",
    "TECH_STACK.md",
    "PERSISTANT.md",
    "DOC_AGENT.md",
    "DOC_INDEX.md",
]

DOC_DESCRIPTIONS = {
    "BACKEND_STRUCTURE.md": "Schema, storage, and API shape.",
    "IMPLEMENTATION_PLAN.md": "Phases and milestones.",
    "TECH_STACK.md": "Runtime, tooling, dependencies.",
    "PERSISTANT.md": "Operational rules and constraints.",
    "DOC_AGENT.md": "Doc agent behavior and configuration.",
    "DOC_INDEX.md": "Auto-generated doc index.",
    "canonical-docs-v2.md": "Authoritative PRD, flows, and rules.",
    "progress.txt": "Status snapshot and feature log.",
}

TYPE_NAMES = {"String", "Text", "Integer", "Float", "Boolean", "DateTime"}
DOC_AGENT_DEFAULT_KEYS = {
    "DOC_AGENT_AUTOCOMMIT",
    "DOC_AGENT_COMMIT_MSG",
    "DOC_AGENT_SUMMARY_CMD",
}
DOC_AGENT_CONFIG_RE = re.compile(
    r"(DOC_AGENT_[A-Z_]+)=('([^']*)'|\"([^\"]*)\"|([^\\s`]+))"
)


class DocAgentError(RuntimeError):
    pass


def run_git(args: List[str], cwd: Path = ROOT_DIR) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def git_available() -> bool:
    try:
        run_git(["rev-parse", "--is-inside-work-tree"])
        return True
    except Exception:
        return False


def get_commit_subject() -> str:
    try:
        return run_git(["log", "-1", "--pretty=%s"])
    except Exception:
        return "Manual run"


def get_commit_sha() -> str:
    try:
        return run_git(["rev-parse", "--short", "HEAD"])
    except Exception:
        return "unknown"


def get_changed_files() -> List[str]:
    try:
        output = run_git(["show", "--name-only", "--pretty=format:", "HEAD"])
        return [line.strip() for line in output.splitlines() if line.strip()]
    except Exception:
        return []


def get_diff_text() -> str:
    try:
        return run_git(["show", "--pretty=", "HEAD"])
    except Exception:
        return ""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def ensure_doc_templates() -> List[Path]:
    created: List[Path] = []
    for name in DOC_FILES:
        path = ROOT_DIR / name
        if path.exists():
            continue
        content = default_doc_template(name)
        path.write_text(content, encoding="utf-8")
        created.append(path)
    return created


def default_doc_template(name: str) -> str:
    if name == "BACKEND_STRUCTURE.md":
        return """# BACKEND_STRUCTURE.md

Status: canonical summary + auto-generated schema sections. Source of truth: canonical-docs-v2.md.

## Architecture (Manual)
- API: FastAPI (apps/api)
- Worker: Python worker (apps/worker)
- DB: SQLite + FTS5 (data/db.sqlite)
- File store: data/archive (originals + derived)

## Data Model (Auto)
<!-- DOC-AGENT:START schema -->
<!-- DOC-AGENT:END schema -->

## Cross-References
<!-- DOC-AGENT:START xrefs -->
<!-- DOC-AGENT:END xrefs -->
"""
    if name == "TECH_STACK.md":
        return """# TECH_STACK.md

Status: canonical summary + auto-generated dependency list.

## Runtime & Toolchain (Manual)
- Python 3.12.x
- FastAPI + Uvicorn
- SQLite 3.46.x
- Git 2.46.x
- Optional: ChromaDB, Ollama

## Python Dependencies (Auto)
<!-- DOC-AGENT:START python_deps -->
<!-- DOC-AGENT:END python_deps -->

## Cross-References
<!-- DOC-AGENT:START xrefs -->
<!-- DOC-AGENT:END xrefs -->
"""
    if name == "IMPLEMENTATION_PLAN.md":
        return """# IMPLEMENTATION_PLAN.md

Status: canonical summary. Update manually as phases evolve.

## Phases (Manual)
- Phase 0: Repo setup
- Phase 1: Backend foundation
- Phase 2: Storage + ingestion
- Phase 3: Indexing + search
- Phase 4: Intelligence (RAG)
- Phase 5: UX polish + release

## Cross-References
<!-- DOC-AGENT:START xrefs -->
<!-- DOC-AGENT:END xrefs -->
"""
    if name == "PERSISTANT.md":
        return """# PERSISTANT.md

Operational rules (keep in sync with canonical-docs-v2.md).

## Rules (Manual)
- Local-first, offline-capable.
- No cloud LLMs; optional local LLM only.
- Deterministic file naming and schema versioning.
- Type safety; avoid Any.
- Files are the source of truth.

## Cross-References
<!-- DOC-AGENT:START xrefs -->
<!-- DOC-AGENT:END xrefs -->
"""
    if name == "DOC_INDEX.md":
        return """# DOC_INDEX.md

<!-- DOC-AGENT:START index -->
<!-- DOC-AGENT:END index -->
"""
    if name == "DOC_AGENT.md":
        return """# DOC_AGENT.md

Doc agent runs post-commit to keep docs aligned with code changes.

## Usage
- Manual: `python3 infra/scripts/doc_agent.py --mode manual`
- Install post-commit hook: `bash infra/scripts/install_doc_agent_hook.sh`

## Behavior
- Appends to `progress.txt` feature log
- Refreshes schema and dependency sections
- Updates cross-references and index
- Optionally auto-commits doc updates

## Configuration
- Defaults are read from this file when the environment variable is unset.
- `DOC_AGENT_AUTOCOMMIT=1` to auto-commit
- `DOC_AGENT_COMMIT_MSG="Auto-doc: ..."`
- `DOC_AGENT_SUMMARY_CMD="..."` to generate summaries (stdin diff)
"""
    raise DocAgentError(f"No template for {name}")


def replace_section(text: str, start_marker: str, end_marker: str, new_block: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end < start:
        return text
    before = text[: start + len(start_marker)]
    after = text[end:]
    return f"{before}\n{new_block}\n{after}"


def update_backend_structure() -> bool:
    target = ROOT_DIR / "BACKEND_STRUCTURE.md"
    models_path = ROOT_DIR / "apps" / "api" / "app" / "db" / "models.py"
    if not target.exists() or not models_path.exists():
        return False

    tables = extract_tables(models_path)
    lines: List[str] = []
    for table in tables:
        lines.append(f"### {table['name']}")
        for col in table["columns"]:
            details = []
            if col.get("type"):
                details.append(col["type"])
            if col.get("pk"):
                details.append("PK")
            if col.get("unique"):
                details.append("unique")
            if col.get("fk"):
                details.append(f"FK {col['fk']}")
            if col.get("nullable") is False:
                details.append("not null")
            detail_text = f" ({', '.join(details)})" if details else ""
            lines.append(f"- {col['name']}{detail_text}")
        lines.append("")
    new_block = "\n".join(lines).rstrip() if lines else "- No tables found."

    content = read_text(target)
    updated = replace_section(
        content,
        "<!-- DOC-AGENT:START schema -->",
        "<!-- DOC-AGENT:END schema -->",
        new_block,
    )
    return write_text_if_changed(target, updated)


def extract_tables(models_path: Path) -> List[dict]:
    source = read_text(models_path)
    tree = ast.parse(source)
    tables: List[dict] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        table_name: Optional[str] = None
        columns: List[dict] = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(stmt.value, ast.Constant):
                            table_name = str(stmt.value.value)
            if isinstance(stmt, ast.AnnAssign):
                col = parse_column(stmt)
                if col:
                    columns.append(col)
        if table_name and columns:
            tables.append({"name": table_name, "columns": columns})
    return tables


def parse_column(stmt: ast.AnnAssign) -> Optional[dict]:
    if not isinstance(stmt.target, ast.Name):
        return None
    name = stmt.target.id
    call = stmt.value
    if not isinstance(call, ast.Call):
        return None
    func = call.func
    if not (isinstance(func, ast.Name) and func.id == "mapped_column"):
        return None

    type_name: Optional[str] = None
    fk_target: Optional[str] = None
    for arg in call.args:
        if isinstance(arg, ast.Name) and arg.id in TYPE_NAMES and not type_name:
            type_name = arg.id
        if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "ForeignKey":
            if arg.args and isinstance(arg.args[0], ast.Constant):
                fk_target = str(arg.args[0].value)

    pk = False
    unique = False
    nullable: Optional[bool] = None
    for kw in call.keywords:
        if kw.arg == "primary_key" and isinstance(kw.value, ast.Constant):
            pk = bool(kw.value.value)
        if kw.arg == "unique" and isinstance(kw.value, ast.Constant):
            unique = bool(kw.value.value)
        if kw.arg == "nullable" and isinstance(kw.value, ast.Constant):
            nullable = bool(kw.value.value)

    return {
        "name": name,
        "type": type_name,
        "pk": pk,
        "unique": unique,
        "fk": fk_target,
        "nullable": nullable,
    }


def update_tech_stack() -> bool:
    target = ROOT_DIR / "TECH_STACK.md"
    lock_path = ROOT_DIR / "requirements.lock"
    if not target.exists() or not lock_path.exists():
        return False

    deps = []
    for line in read_text(lock_path).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        deps.append(line)
    dep_lines = [f"- {dep}" for dep in deps] if deps else ["- No dependencies found."]
    new_block = "\n".join(dep_lines)

    content = read_text(target)
    updated = replace_section(
        content,
        "<!-- DOC-AGENT:START python_deps -->",
        "<!-- DOC-AGENT:END python_deps -->",
        new_block,
    )
    return write_text_if_changed(target, updated)


def update_doc_index() -> bool:
    target = ROOT_DIR / "DOC_INDEX.md"
    if not target.exists():
        return False

    entries: List[str] = []
    all_docs: List[str] = [
        *DOC_FILES,
        "canonical-docs-v2.md",
        "progress.txt",
    ]
    for name in all_docs:
        path = ROOT_DIR / name
        if not path.exists():
            continue
        description = DOC_DESCRIPTIONS.get(name, "")
        label = f"[{name}]({name})"
        if description:
            entries.append(f"- {label} - {description}")
        else:
            entries.append(f"- {label}")

    new_block = "\n".join(entries) if entries else "- No docs found."
    content = read_text(target)
    updated = replace_section(
        content,
        "<!-- DOC-AGENT:START index -->",
        "<!-- DOC-AGENT:END index -->",
        new_block,
    )
    return write_text_if_changed(target, updated)


def update_cross_references() -> List[Path]:
    updated: List[Path] = []
    docs_present = [name for name in DOC_FILES if (ROOT_DIR / name).exists()]
    cross_ref_targets = [
        name
        for name in [*docs_present, "canonical-docs-v2.md", "progress.txt"]
        if (ROOT_DIR / name).exists()
    ]

    for name in docs_present:
        path = ROOT_DIR / name
        content = read_text(path)
        links = [
            f"- [{other}]({other})"
            for other in cross_ref_targets
            if other != name
        ]
        new_block = "\n".join(links) if links else "- None."
        updated_content = replace_section(
            content,
            "<!-- DOC-AGENT:START xrefs -->",
            "<!-- DOC-AGENT:END xrefs -->",
            new_block,
        )
        if write_text_if_changed(path, updated_content):
            updated.append(path)
    return updated


def generate_summary(diff_text: str, changed_files: List[str], commit_subject: str) -> str:
    cmd = os.getenv("DOC_AGENT_SUMMARY_CMD")
    if cmd:
        try:
            result = subprocess.run(
                cmd,
                input=diff_text,
                text=True,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            summary = result.stdout.strip()
            if summary:
                return summary
        except Exception:
            pass

    categories = []
    if any(f.startswith("apps/api/") for f in changed_files):
        categories.append("API")
    if any(f.startswith("apps/worker/") for f in changed_files):
        categories.append("Worker")
    if any(f.startswith("infra/") for f in changed_files):
        categories.append("Infra")
    if any(f.startswith("packages/") for f in changed_files):
        categories.append("Shared")
    if not categories:
        categories.append("Repo")

    category_text = ", ".join(categories)
    if commit_subject:
        return f"{commit_subject} ({category_text})"
    return f"Repository update ({category_text})"


def append_progress_log(changed_files: List[str], summary: str, changed_docs: List[str]) -> bool:
    progress_path = ROOT_DIR / "progress.txt"
    if not progress_path.exists():
        return False

    content = read_text(progress_path)
    lines = content.splitlines()
    try:
        pipeline_idx = lines.index("PIPELINE HEALTH")
    except ValueError:
        return False

    insert_idx = pipeline_idx - 1
    while insert_idx > 0 and lines[insert_idx].strip() != "========================================":
        insert_idx -= 1

    today = dt.date.today().isoformat()
    sha = get_commit_sha()
    subject = get_commit_subject()

    entry_lines = [
        f"[{today}] Auto-doc: {summary}",
        f"- Commit: {sha} \"{subject}\"",
    ]
    if changed_files:
        entry_lines.append("- Changed files:")
        for name in changed_files:
            entry_lines.append(f"  - {name}")
    if changed_docs:
        entry_lines.append("- Docs updated:")
        for name in changed_docs:
            entry_lines.append(f"  - {name}")

    entry_lines.append("")

    new_lines = lines[:insert_idx] + entry_lines + lines[insert_idx:]
    new_content = "\n".join(new_lines) + "\n"
    return write_text_if_changed(progress_path, new_content)


def git_status_dirty() -> bool:
    try:
        status = run_git(["status", "--porcelain"])
        return bool(status.strip())
    except Exception:
        return False


def git_add(paths: Iterable[Path]) -> None:
    args = ["add", "--"] + [str(path.relative_to(ROOT_DIR)) for path in paths]
    run_git(args)


def git_commit(message: str) -> None:
    env = os.environ.copy()
    env["DOC_AGENT_SKIP"] = "1"
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=ROOT_DIR,
        env=env,
        check=True,
    )


def load_doc_agent_defaults() -> None:
    path = ROOT_DIR / "DOC_AGENT.md"
    if not path.exists():
        return
    try:
        content = read_text(path)
    except OSError:
        return
    for match in DOC_AGENT_CONFIG_RE.finditer(content):
        key = match.group(1)
        if key not in DOC_AGENT_DEFAULT_KEYS:
            continue
        if os.getenv(key):
            continue
        value = match.group(3) or match.group(4) or match.group(5) or ""
        if value:
            os.environ[key] = value


def main() -> int:
    parser = argparse.ArgumentParser(description="Doc agent for LetterOps")
    parser.add_argument("--mode", choices=["post-commit", "manual"], default="manual")
    parser.add_argument("--auto-commit", action="store_true", default=False)
    parser.add_argument("--no-auto-commit", action="store_true", default=False)
    args = parser.parse_args()

    if os.getenv("DOC_AGENT_SKIP") == "1":
        return 0

    load_doc_agent_defaults()

    if not git_available():
        print("Doc agent: git not available", file=sys.stderr)
        return 1

    subject = get_commit_subject()
    if args.mode == "post-commit" and subject.startswith("Auto-doc:"):
        return 0

    created_docs = ensure_doc_templates()

    changed_files = get_changed_files()
    diff_text = get_diff_text()
    summary = generate_summary(diff_text, changed_files, subject)

    changed_docs: List[str] = []
    if update_backend_structure():
        changed_docs.append("BACKEND_STRUCTURE.md")
    if update_tech_stack():
        changed_docs.append("TECH_STACK.md")
    if update_doc_index():
        changed_docs.append("DOC_INDEX.md")

    for path in update_cross_references():
        changed_docs.append(path.name)
    for path in created_docs:
        changed_docs.append(path.name)

    changed_docs = list(dict.fromkeys(changed_docs))
    if append_progress_log(changed_files, summary, changed_docs):
        changed_docs.append("progress.txt")
    changed_docs = list(dict.fromkeys(changed_docs))

    if not git_status_dirty():
        return 0

    auto_commit = args.auto_commit
    if args.mode == "post-commit":
        if os.getenv("DOC_AGENT_AUTOCOMMIT", "1") == "0":
            auto_commit = False
        elif not args.no_auto_commit:
            auto_commit = True

    if auto_commit:
        message = os.getenv("DOC_AGENT_COMMIT_MSG")
        if not message:
            message = f"Auto-doc: Update docs for {get_commit_sha()}"
        paths = [ROOT_DIR / name for name in DOC_FILES if (ROOT_DIR / name).exists()]
        if (ROOT_DIR / "progress.txt").exists():
            paths.append(ROOT_DIR / "progress.txt")
        git_add(paths)
        git_commit(message)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
