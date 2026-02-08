# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LetterOps is a local-first document intelligence system for managing Bahá'í letter archives. It ingests letters, preserves originals immutably, extracts metadata deterministically, and provides structured/semantic retrieval via FTS5. The authoritative PRD is `canonical-docs-v2.md`.

## Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest apps/api/tests/test_health.py -v

# Run worker tests only
pytest apps/worker/tests/

# Generate repo snapshot
make snapshot

# Snapshot + run tests
make verify

# Start API server (from apps/api/)
uvicorn app.main:app --reload

# Run Alembic migrations (from apps/api/)
alembic upgrade head

# Ingest a single document
python apps/worker/ingest_file.py /path/to/document.pdf
```

## Architecture

**Monorepo layout:**
- `apps/api/` — FastAPI backend (auth, health, config, DB models, migrations)
- `apps/worker/` — Document ingestion pipeline and processing utilities
- `infra/` — Alembic migrations (`infra/migrations/`), seed data, scripts
- `data/` — SQLite DB (`db.sqlite`), `archive/` (immutable originals), `metadata/` (sidecar JSON)

**Tech stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, SQLite with FTS5, structlog. Linting: ruff. Formatting: black. Types: mypy.

**Ingestion pipeline** (`apps/worker/pipeline.py`):
hash → dedupe → archive → extract → convert → index → link → tag

Each step is tracked as a `PipelineStep` record in the DB. The pipeline handles partial failures (e.g., conversion may succeed for txt but fail for md).

**Key data patterns:**
- Document IDs are ULIDs (Crockford base32, 26 chars)
- File deduplication via SHA-256
- Archive paths: `data/archive/{YYYYMM}/{ULID}/{filename}`
- Metadata extraction produces confidence scores (0.0–1.0); low-confidence items are flagged for human review
- API responses use envelope format: `{"data": ..., "error": null}`
- Auth uses JWT in HTTP-only cookies (roles: owner, editor, viewer)

**Database:** SQLite with FTS5 virtual table (`documents_fts`). Schema defined in `infra/migrations/versions/0001_initial.py` and ORM models in `apps/api/app/db/models.py`.

## Operational Rules (from PERSISTANT.md)

- **Local-first**: No cloud LLMs; optional local LLM (Ollama) only
- **Type safety**: Avoid `Any` in type hints
- **Files are source of truth**: DB records reference files, not duplicate content
- **Deterministic**: File naming and schema versioning must be deterministic
- **Commit after major tasks**: Git-version the DB after significant changes

## Configuration

Environment variables are defined in `.env` (see `.env.example`). Key vars: `DATABASE_URL`, `LETTEROPS_JWT_SECRET`, `LETTEROPS_AUTO_SEED`, `LETTEROPS_OWNER_EMAIL`, `LETTEROPS_OWNER_PASSWORD`, `LETTEROPS_SEED_TAGS_PATH`.

## Testing

pytest with `asyncio_default_fixture_loop_scope = function` (see `pytest.ini`). Tests live alongside their apps: `apps/api/tests/` and `apps/worker/tests/`. Each test `conftest.py` adds the repo root to `sys.path` for import resolution.

## Current Status

Phase 3 complete (42% overall). Phases 1–3 done: backend foundation, storage/ingestion core, deterministic extraction + conversion + FTS indexing. Next priorities: link inference, tagging suggestions, role-based guards. See `progress.txt` for detailed status.
