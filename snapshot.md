# LetterOps Snapshot Report

Generated: 2026-02-07T20:23:12
Root: /Users/mschwar/Dropbox/letters

## Progress Summary
Gist: Project: LetterOps Last Updated: 2026-02-08 02:29 (local) ========================================

Project: LetterOps
Last Updated: 2026-02-08 02:29 (local)

========================================
CURRENT STATUS SNAPSHOT
========================================
Phase: 3 (Metadata + Conversion + Linking/Tagging)
Branch: main
Overall Progress: 70%

Done:
- [x] Canonical docs reviewed and merged.
- [x] Phase 0: Initialize repo structure and baseline files.
- [x] Phase 1: Backend foundation (FastAPI bootstrap, schema + migrations, auth scaffold, seeding hooks).
- [x] Phase 2: Storage + ingestion core (hashing, ULID, original archiving, ingestion event/run tracking).
- [x] Phase 3: Deterministic extraction + conversion + indexing wired into ingest.
- [x] Dependencies installed (local venv).
- [x] DB migrations applied (0001_initial).
- [x] Seed defaults executed (tags).
- [x] Unit tests (API + worker) passing.
- [x] Startup migrated to FastAPI lifespan handler.
- [x] pytest-asyncio default loop scope set.

In Progress:
- [ ] None.

Next:
- [ ] Begin Phase 4 planning for intelligence/RAG implementation.

Blocked:
- [ ] None.

========================================
FEATURE LOG (append-only)
========================================
[2026-02-07] Feature: Phase 1 Backend Foundation
- Scope reference: IMPLEMENTATION_PLAN.md Phase 1; BACKEND_STRUCTURE.md schema; PERSISTANT.md rules
- What was built:
  - FastAPI app skeleton with `/health` and `/api/v1/auth` endpoints.
  - Structured logging + config loader.
  - SQLAlchemy models matching canonical schema.
  - Alembic migration `0001_initial` (includes FTS5 virtual table).
  - Seed defaults helper + optional startup seeding.
  - Unit tests for health + security helpers.
- Tests added/updated:
  - `apps/api/tests/test_health.py`
  - `apps/api/tests/test_security.py`
- Result:
  - PASS (2026-02-07, local venv).
- Known gaps:
  - Auth role guards not enforced beyond `/me` dependency.
- Follow-up tasks:
  - Add role-based guards and integration tests.

[2026-02-07] Feature: Phase 2 File & Pipeline Core (baseline)
- Scope reference: IMPLEMENTATION_PLAN.md Phase 2; BACKEND_STRUCTURE.md storage rules
- What was built:
  - Worker config + storage service (deterministic paths, immutable originals).
  - SHA-256 hashing utility.
  - ULID generator (Crockford base32).
  - Ingestion repository helpers (events, runs, steps).
  - CLI ingest flow: hash -> dedupe -> archive.
- Tests added/updated:
  - `apps/worker/tests/test_hashing.py`
  - `apps/worker/tests/test_ulid.py`
- Result:
  - PASS (2026-02-07, local venv).
- Known gaps:
  - Pipeline steps beyond archive were stubbed.
- Follow-up tasks:
  - Extend pipeline steps and add integration tests.

[2026-02-07] Feature: Phase 3 Deterministic Extraction + Conversion
- Scope reference: IMPLEMENTATION_PLAN.md Phase 3; BACKEND_STRUCTURE.md data + storage rules
- What was built:
  - Deterministic metadata extraction (date/source/summary) with confidence scoring.
  - Derivative generation (txt/md) with partial failure handling.
  - Metadata sidecar writer + DB metadata version record.
  - FTS upsert on ingest.
  - Ingest pipeline now runs: hash -> dedupe -> archive -> extract -> convert -> index -> link (skipped).
- Tests added/updated:
  - `apps/worker/tests/test_extraction.py`
  - `apps/worker/tests/test_metadata_sidecar.py`
- Result:
  - PASS (2026-02-07, local venv).
- Known gaps:
  - Linking and tagging suggestions not implemented.
- Follow-up tasks:
  - Add link inference + tagging heuristics.

[2026-02-08] Feature: Linking + Tagging + Auth Guards
- Scope reference: BACKEND_STRUCTURE.md linking/tagging + role access expectations
- What was built:
  - Implemented link inference and document link persistence in pipeline.
  - Implemented tagging heuristics using tags + aliases with persistence in pipeline.
  - Added role guard dependencies and auth integration tests.
- Tests added/updated:
  - `apps/api/tests/test_auth_integration.py`
- Result:
  - Code complete; runtime verification still pending in this environment.
- Known gaps:
  - None.
- Follow-up tasks:
  - Monitor heuristic quality against real letters.

[2026-02-08] Verification: Fresh Sample Ingest (Priority 3)
- Scope reference: progress checklist Priority 3 (verify with data)
- What was run:
  - Installed API/worker dependencies in `.venv` from `apps/api/requirements.txt`.
  - Ingested a fresh sample markdown letter via `apps.worker.ingest_file`.
  - Queried SQLite for run, step, FTS, tag, and link deltas.
- Result:
  - PASS (2026-02-08): new run `d2e448bb-ed2f-495a-bab7-49f919006097` succeeded.
  - Step logs confirm `tag|success|tags=5` and `link|success|links=2`.
  - Table deltas after run: `documents=4`, `document_tags=11`, `document_links=4`, `pipeline_runs=4`, `document_fts=4`.

[2026-02-08] Maintenance: jose utcnow deprecation compatibility
- Scope reference: Next task + automation checklist (jose compatibility)
- What was built:
  - Wrapped JWT decode with targeted warning suppression for `python-jose` utcnow deprecation.
  - Added regression test to assert no utcnow deprecation warning leaks from `decode_token`.
- Tests added/updated:
  - `apps/api/tests/test_security.py`
- Result:
  - PASS (2026-02-08): `pytest` now shows no jose utcnow warning.

[2026-02-08] Maintenance: Snapshot pytest summary
- Scope reference: Automation/Overhead checklist (snapshot pytest summary)
- What was built:
  - Added pytest execution and PASS/FAIL summary to `infra/scripts/generate_snapshot.py`.
  - Added CLI flags `--no-pytest` and `--pytest-timeout`.
  - Snapshot markdown now includes a dedicated `Pytest Summary` section.
- Result:
  - PASS (2026-02-08): snapshot reports `Status: PASS` and test summary line.

========================================
PIPELINE HEALTH
========================================
Latest run IDs:
- run_id:
- run_id:

Failure patterns observed:
- None recorded.

Reliability notes:
- None recorded.

========================================
TECH DEBT / IMPROVEMENTS
========================================
- [ ] Align local runtime to Python 3.12.6 (currently 3.13.2).

========================================
NEXT STEPS CHECKLIST (PRIORITIZED)
========================================
Priority 1: Expand Pipeline (Linking + Tagging)
- [x] Implement link inference (date/source cues per BACKEND_STRUCTURE.md) and persist to `document_links`.
- [x] Implement tagging heuristics (controlled vocab from `tags`/`tag_aliases`) and persist to `document_tags`.
- [x] Integrate linking + tagging into the ingest pipeline (complete skipped step).
Parallel lanes: linking vs tagging.

Priority 2: Phase 1 Follow-Ups
- [x] Implement role-based guards (FastAPI dependencies).
- [x] Add auth integration tests.
Parallel lanes: guards vs tests.

Priority 3: Verify with Data
- [x] Run sample ingest (e.g., Bahá’í letter PDF) to populate DB.
- [x] Validate current FTS/indexing, tags, links, and pipeline run records.
Parallel lanes: ingest vs validation/perf checks.

Automation / Overhead
- [x] Align runtime to Python 3.12.6; patch jose compatibility if needed.
- [x] Enhance snapshot script with pytest summary (PASS/FAIL).

========================================
RELEASE CHECKLIST (v1)
========================================
- [ ] All PRD acceptance criteria validated
- [ ] Backup/restore round-trip tested
- [ ] Search latency target met
- [ ] Documentation complete
- [ ] Security checks complete

Keywords: 2026, phase, tests, pipeline, pytest, run, ingest, scope, tagging, backend

## Git State
Branch: main
Status:
## main...origin/main [ahead 1]
 M apps/api/app/core/security.py
 M apps/api/tests/test_security.py
 M infra/scripts/generate_snapshot.py
 M progress.txt
 M snapshot.md
Recent commits:
c880c5e Verify ingest pipeline after dependency install
b52603c Expand pipeline linking/tagging and add auth guards
c26d497 Document commit-after-major-task rule
bd440b1 Add deterministic extraction, conversion, and FTS indexing
b9a7085 Create snapshot.md
Diff summary:
(no diffs)

## Pytest Summary
Status: PASS
Summary: 10 passed, 1 warning in 1.83s

## canonical-docs-v2.md Excerpt
Gist: # PRD.md (Revised v2) ## 1) Product Overview LetterOps is a local-first document intelligence app for letter-heavy knowledge workflows (starting with Bahá’í letters). It ingests letters from email and watched folders, preserves originals, creates normalized derivatives, extracts metadata, links references, and provides fast retrieval by date/source/topic/reference. +Revised: Integrated Gemini's se...

# PRD.md (Revised v2)

## 1) Product Overview

LetterOps is a local-first document intelligence app for letter-heavy knowledge workflows (starting with Bahá’í letters). It ingests letters from email and watched folders, preserves originals, creates normalized derivatives, extracts metadata, links references, and provides fast retrieval by date/source/topic/reference. +Revised: Integrated Gemini's semantic search (optional RAG) for natural-language queries, while keeping GPT's structured focus.

**Primary outcome:** A reliable system that replaces memory burden with structured retrieval.

## 2) Who It’s For

- Primary user: Individual researcher/reader maintaining a personal letter archive (e.g., tech-savvy Bahá’í user).
- Secondary user: Small study/admin teams (2–5 users) in future version. +Kept: Aligns with both; Gemini's "tech-savvy" emphasis added for clarity.

## 3) Problem Statement

Users can file letters chronologically, but struggle to:

- quickly retrieve referenced prior letters,
- maintain consistency in tagging/summaries,
- preserve provenance and version history,
- avoid duplicate/manual processing toil. +Kept: GPT's core; added Gemini's "thematic correlation" to pro
... (truncated)

Keywords: letters, geminis, user, revised, letter, baháí, retrieval, gpts, structured, primary

## README.md Excerpt
Gist: # LetterOps Local-first document intelligence system for managing Bahá’í letters. See `canonical-docs-v2.md` for the authoritative PRD, flows, tech stack, and operating rules. ## Monorepo Layout

# LetterOps

Local-first document intelligence system for managing Bahá’í letters. See `canonical-docs-v2.md` for the authoritative PRD, flows, tech stack, and operating rules.

## Monorepo Layout
- `apps/web`: Next.js UI
- `apps/api`: FastAPI backend
- `apps/worker`: local ingestion worker
- `packages/shared`: shared schemas/types
- `infra`: migrations, scripts, backup tooling
- `data/db.sqlite`: versioned SQLite database

## Quick Start (Backend)
1. Create a virtualenv and install dependencies from `apps/api/requirements.txt`.
2. Set env vars in `.env` (see `.env.example` if present).
3. Run migrations using Alembic.
4. Start the API with `uvicorn app.main:app --reload` from `apps/api`.

Keywords: local, see, appsapi, backend, migrations, start, env, letterops, first, document

## DB Snapshot
Path: /Users/mschwar/Dropbox/letters/data/db.sqlite
Size (bytes): 364544
Tables:
- alembic_version (rows: 1)
- audit_events (rows: 0)
- document_files (rows: 12)
- document_fts (rows: 4)
- document_fts_config (rows: 1)
- document_fts_content (rows: 4)
- document_fts_data (rows: 32)
- document_fts_docsize (rows: 4)
- document_fts_idx (rows: 30)
- document_links (rows: 4)
- document_metadata_versions (rows: 4)
- document_tags (rows: 11)
- documents (rows: 4)
- ingestion_events (rows: 4)
- pipeline_runs (rows: 4)
- pipeline_steps (rows: 32)
- sources (rows: 0)
- tag_aliases (rows: 0)
- tags (rows: 5)
- users (rows: 1)

Schema:
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
)
CREATE TABLE audit_events (
	id VARCHAR NOT NULL, 
	actor_user_id VARCHAR, 
	action VARCHAR NOT NULL, 
	object_type VARCHAR NOT NULL, 
	object_id VARCHAR NOT NULL, 
	before_json TEXT, 
	after_json TEXT, 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_user_id) REFERENCES users (id)
)
CREATE TABLE document_files (
	id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	file_kind VARCHAR NOT NULL CHECK (file_kind IN ('original','pdf','txt','md','docx')), 
	path TEXT NOT NULL, 
	mime_type VARCHAR, 
	bytes INTEGER, 
	checksum_sha256 VARCHAR NOT NULL, 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_document_files_doc_kind UNIQUE (document_id, file_kind), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
)
CREATE VIRTUAL TABLE document_fts USING fts5(document_id UNINDEXED, title, summary, full_text, source_name, tags)
CREATE TABLE 'document_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID
CREATE TABLE 'document_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3, c4, c5)
CREATE TABLE 'document_fts_data'(id INTEGER PRIMARY KEY, block BLOB)
CREATE TABLE 'document_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB)
CREATE TABLE 'document_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID
CREATE TABLE document_links (
	id VARCHAR NOT NULL, 
	from_document_id VARCHAR NOT NULL, 
	to_document_id VARCHAR NOT NULL, 
	link_type VARCHAR NOT NULL CHECK (link_type IN ('references','clarifies','supersedes','related')), 
	confidence FLOAT DEFAULT 1 NOT NULL, 
	state VARCHAR NOT NULL CHECK (state IN ('suggested','confirmed','rejected')), 
	created_by VARCHAR NOT NULL CHECK (created_by IN ('system','user')), 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_document_links UNIQUE (from_document_id, to_document_id, link_type), 
	FOREIGN KEY(from_document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(to_document_id) REFERENCES documents (id) ON DELETE CASCADE
)
CREATE TABLE document_metadata_versions (
	id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	version_no INTEGER NOT NULL, 
	metadata_json TEXT NOT NULL, 
	edited_by_user_id VARCHAR, 
	edit_reason TEXT, 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_metadata_version UNIQUE (document_id, version_no), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(edited_by_user_id) REFERENCES users (id)
)
CREATE TABLE document_tags (
	document_id VARCHAR NOT NULL, 
	tag_id VARCHAR NOT NULL, 
	confidence FLOAT DEFAULT 1 NOT NULL, 
	assigned_by VARCHAR NOT NULL CHECK (assigned_by IN ('system','user')), 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (document_id, tag_id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	FOREIGN KEY(tag_id) REFERENCES tags (id) ON DELETE CASCADE
)
CREATE TABLE documents (
	id VARCHAR NOT NULL, 
	sha256 VARCHAR NOT NULL, 
	canonical_title VARCHAR, 
	source_name VARCHAR, 
	audience VARCHAR, 
	document_date VARCHAR, 
	document_type VARCHAR, 
	summary_one_sentence TEXT, 
	confidence_overall FLOAT DEFAULT 0 NOT NULL, 
	status VARCHAR NOT NULL CHECK (status IN ('ingested','indexed','needs_review','archived','failed')), 
	archive_path TEXT NOT NULL, 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_documents_sha256 UNIQUE (sha256)
)
CREATE TABLE ingestion_events (
	id VARCHAR NOT NULL, 
	source_id VARCHAR, 
	trigger_type VARCHAR NOT NULL CHECK (trigger_type IN ('file_watch','eml_import','manual_upload','retry')), 
	payload_json TEXT NOT NULL, 
	event_time TEXT NOT NULL, 
	status VARCHAR NOT NULL CHECK (status IN ('received','processed','failed')), 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_id) REFERENCES sources (id)
)
CREATE TABLE pipeline_runs (
	id VARCHAR NOT NULL, 
	ingestion_event_id VARCHAR, 
	document_id VARCHAR, 
	status VARCHAR NOT NULL CHECK (status IN ('running','success','partial_failed','failed')), 
	started_at TEXT NOT NULL, 
	ended_at TEXT, 
	error_summary TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ingestion_event_id) REFERENCES ingestion_events (id), 
	FOREIGN KEY(document_id) REFERENCES documents (id)
)
CREATE TABLE pipeline_steps (
	id VARCHAR NOT NULL, 
	run_id VARCHAR NOT NULL, 
	step_name VARCHAR NOT NULL, 
	status VARCHAR NOT NULL CHECK (status IN ('running','success','failed','skipped')), 
	started_at TEXT NOT NULL, 
	ended_at TEXT, 
	logs TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES pipeline_runs (id) ON DELETE CASCADE
)
CREATE TABLE sources (
	id VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL CHECK (kind IN ('watch_folder','eml_import','manual_upload')), 
	name VARCHAR NOT NULL, 
	config_json TEXT NOT NULL, 
	is_active INTEGER DEFAULT 1 NOT NULL, 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id)
)
CREATE TABLE tag_aliases (
	id VARCHAR NOT NULL, 
	tag_id VARCHAR NOT NULL, 
	alias VARCHAR NOT NULL, 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tag_id) REFERENCES tags (id) ON DELETE CASCADE, 
	UNIQUE (alias)
)
CREATE TABLE tags (
	id VARCHAR NOT NULL, 
	"key" VARCHAR NOT NULL, 
	label VARCHAR NOT NULL, 
	parent_tag_id VARCHAR, 
	is_active INTEGER DEFAULT 1 NOT NULL, 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE ("key"), 
	FOREIGN KEY(parent_tag_id) REFERENCES tags (id)
)
CREATE TABLE users (
	id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	password_hash VARCHAR NOT NULL, 
	role VARCHAR NOT NULL CHECK (role IN ('owner','editor','viewer')), 
	created_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	updated_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)

Recent pipeline_runs:
id, status, started_at
d2e448bb-ed2f-495a-bab7-49f919006097, success, 2026-02-08T02:19:33.244788+00:00
2e4ab680-716a-4348-ad02-13c306f115a8, success, 2026-02-08T02:04:29.065117+00:00
4b15772a-bdf3-4a42-a855-7e4a5e4ad652, success, 2026-02-08T02:04:25.299691+00:00
ce9ca3a5-70d3-498b-8bb4-c0f40a89787a, success, 2026-02-08T02:04:19.596460+00:00

## Repo Structure
/Users/mschwar/Dropbox/letters
├── BACKEND_STRUCTURE.md
├── CLAUDE.md
├── DOC_AGENT.md
├── DOC_INDEX.md
├── IMPLEMENTATION_PLAN.md
├── Makefile
├── PERSISTANT.md
├── README.md
├── TECH_STACK.md
├── apps
│   ├── __init__.py
│   ├── __pycache__
│   ├── api
│   └── worker
├── archive
│   ├── GPT-5.2.md
│   ├── Gemini.md
│   └── Welcome.md
├── canonical-docs-v2.md
├── data
│   ├── archive
│   ├── db.sqlite
│   ├── metadata
│   └── runs
├── infra
│   ├── hooks
│   ├── migrations
│   ├── scripts
│   └── seeds
├── packages
│   └── shared
├── progress.txt
├── pytest.ini
├── requirements.lock
└── snapshot.md

17 directories, 19 files
