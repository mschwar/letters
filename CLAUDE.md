# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LetterOps is a local-first document intelligence system for managing Bahá'í letter archives. It ingests letters, preserves originals immutably, extracts metadata deterministically, and provides structured/semantic retrieval via FTS5 + optional vector search. The authoritative PRD is `canonical-docs-v2.md`.

## Commands

```bash
# Backend
pytest                                       # Run all tests
pytest apps/api/tests/test_health.py -v      # Run specific test file
pytest apps/worker/tests/                    # Run worker tests only
uvicorn app.main:app --reload                # Start API server (run from apps/api/)
alembic upgrade head                         # Run migrations (run from apps/api/)
python apps/worker/ingest_file.py /path/to/doc.pdf  # Ingest a single document

# Web frontend (apps/web is a Next.js app)
make web-install                             # npm install
make web-dev                                 # Next.js dev server
make web-build                               # Production build
make web-e2e-install                         # Install Playwright browsers
make web-e2e                                 # Run Playwright E2E tests

# Quality gates
make verify                                  # Snapshot + pytest
make search-gate                             # Judged-set retrieval quality gate
make release-check                           # Full release gate (verify + search-gate + backup-roundtrip + security-check)
make snapshot                                # Generate repo snapshot
```

## Architecture

**Monorepo layout:**
- `apps/api/` — FastAPI backend (auth, health, search, config, DB models)
- `apps/worker/` — Document ingestion pipeline and processing utilities
- `apps/web/` — Next.js frontend (search UI, auth, citation display)
- `infra/` — Alembic migrations (`infra/migrations/`), seed data, scripts (eval, backup, scraper)
- `data/` — SQLite DB (`db.sqlite`), `archive/` (immutable originals + derived files), `metadata/` (sidecar JSON), `vectors/` (ChromaDB)

**Tech stack:**
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic, SQLite with FTS5, ChromaDB (optional vectors), structlog
- Frontend: Next.js 16, React 18, TypeScript, Playwright
- Linting: ruff. Formatting: black. Types: mypy
- CI: GitHub Actions (`.github/workflows/ci.yml`) — runs backend pytest + web build/lint/typecheck/e2e

**Import conventions:** API code uses `app.*` imports (e.g., `from app.core.config import settings`). Worker code uses `apps.worker.*` imports (e.g., `from apps.worker.hashing import sha256_file`). The pipeline (`apps/worker/pipeline.py`) cross-imports DB models from the API via `from app.db.models import ...`. Test `conftest.py` files add the repo root to `sys.path`.

**Ingestion pipeline** (`apps/worker/pipeline.py`):
hash → dedupe → archive → extract → convert → tag → index → link

Each step is tracked as a `PipelineStep` record in the DB. The pipeline handles partial failures (e.g., conversion may succeed for txt but fail for md). Documents with confidence < 0.6 get status `needs_review`.

**Search & retrieval** (`apps/api/app/routers/search_router.py`):
- `POST /api/v1/search` — authenticated endpoint supporting FTS, vector, or hybrid retrieval
- Hybrid mode uses weighted reciprocal-rank fusion (RRF) over FTS + vector results
- Fusion weights configurable via `LETTEROPS_SEARCH_FUSION_*` env vars
- Vector backend (ChromaDB) is optional; gracefully falls back to FTS when unavailable
- Quality measured via `infra/scripts/evaluate_search.py` against judged query set in `data/eval/`

**Key data patterns:**
- Document IDs are ULIDs (Crockford base32, 26 chars)
- File deduplication via SHA-256
- Archive paths: `data/archive/originals/{YYYY}/{MM}/{DD}/{ULID}/{filename}` (originals) and `data/archive/derived/{ULID}/` (txt/md conversions)
- Metadata extraction produces confidence scores (0.0–1.0); low-confidence items flagged for review
- API responses use envelope format: `{"data": ..., "error": null}`
- Auth uses JWT in HTTP-only cookies (roles: owner, editor, viewer)
- Role guards via FastAPI dependencies: `require_owner`, `require_editor`, `require_viewer` in `app/core/deps.py`

**Database:** SQLite with FTS5 virtual table (`documents_fts`). Schema in `infra/migrations/versions/0001_initial.py`, ORM models in `apps/api/app/db/models.py`.

## Operational Rules (from PERSISTANT.md)

- **Local-first**: No cloud LLMs; optional local LLM (Ollama) only
- **Type safety**: Avoid `Any` in type hints
- **Files are source of truth**: DB records reference files, not duplicate content
- **Deterministic**: File naming and schema versioning must be deterministic
- **Commit after major tasks**: Git-version the DB after significant changes

## Configuration

Environment variables defined in `.env` (see `.env.example`). Key vars: `DATABASE_URL`, `LETTEROPS_JWT_SECRET`, `LETTEROPS_AUTO_SEED`, `LETTEROPS_OWNER_EMAIL`, `LETTEROPS_OWNER_PASSWORD`, `LETTEROPS_SEED_TAGS_PATH`. Vector search: `LETTEROPS_VECTOR_SEARCH` (0/1), `LETTEROPS_VECTOR_PROVIDER`, `LETTEROPS_VECTOR_DIR`. Fusion tuning: `LETTEROPS_SEARCH_FUSION_FTS_WEIGHT`, `LETTEROPS_SEARCH_FUSION_VECTOR_WEIGHT`, `LETTEROPS_SEARCH_FUSION_RRF_K`.

Dependencies are pinned in `requirements.lock` (referenced by `apps/api/requirements.txt`).

## Testing

pytest with `asyncio_default_fixture_loop_scope = function` (see `pytest.ini`). Tests live alongside their apps: `apps/api/tests/` and `apps/worker/tests/`. Each test `conftest.py` adds the repo root to `sys.path` for import resolution. Web E2E tests use Playwright in `apps/web/`.

## Current Status

All phases complete (v1.0 released). See `progress.txt` for detailed feature log and remaining tech debt.
