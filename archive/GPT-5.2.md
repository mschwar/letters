# PRD.md

# LetterOps — Product Requirements Document (PRD)

## 1) Product Overview
LetterOps is a local-first document intelligence app for letter-heavy knowledge workflows (starting with Bahá’í letters).  
It ingests letters from email and watched folders, preserves originals, creates normalized derivatives, extracts metadata, links references, and provides fast retrieval by date/source/topic/reference.

**Primary outcome:** A reliable system that replaces memory burden with structured retrieval.

## 2) Who It’s For
- Primary user: Individual researcher/reader maintaining a personal letter archive.
- Secondary user: Small study/admin teams (2–5 users) in future version.

## 3) Problem Statement
Users can file letters chronologically, but struggle to:
- quickly retrieve referenced prior letters,
- maintain consistency in tagging/summaries,
- preserve provenance and version history,
- avoid duplicate/manual processing toil.

## 4) Product Goals
1. Ingest all new letters with deterministic metadata capture.
2. Preserve original files immutably and generate standardized derivatives.
3. Provide sub-5-second retrieval for common queries.
4. Surface references between letters as first-class links.
5. Keep human review where model confidence is low.

## 5) Non-Goals (Explicitly Out of Scope for v1)
- No autonomous legal/theological interpretation.
- No public sharing or publishing portal.
- No mobile-native app.
- No full OCR pipeline for poor scans (OCR only optional helper if needed).
- No multi-tenant enterprise RBAC beyond basic owner/editor roles.

## 6) In Scope (v1)
- Email/file-triggered ingestion pipeline
- Hashing, dedupe, provenance tracking
- Metadata extraction + confidence scoring
- Tag taxonomy + controlled vocabulary
- Reference extraction/linking
- Search (structured + full text)
- Archive browser and document detail views
- Pipeline run logs and error handling
- Export/backup of DB + files + metadata sidecars

## 7) User Stories
1. As a user, when a new letter arrives, I want it automatically indexed and filed so I don’t do repetitive manual work.
2. As a user, when a current letter references an earlier one, I want one-click retrieval of that prior letter.
3. As a user, I want to trust the archive: originals immutable, provenance visible, duplicates detected.
4. As a user, I want low-confidence metadata flagged for review before finalization.
5. As a user, I want to search by date/source/topic/tags/reference and open preferred format (pdf/txt/md/docx).

## 8) Feature Requirements & Acceptance Criteria

## F1. Ingestion Triggers
- Sources: watched directory, .eml files, manual upload.
- On trigger, system creates ingestion event and pipeline run.

**Acceptance criteria**
- New file appears -> ingestion starts in <= 5s.
- Unsupported file type is logged and marked failed with reason.
- Duplicate content is not re-processed as new document.

## F2. Canonical Storage & Integrity
- Store immutable original.
- Compute SHA-256 hash on ingest.
- Assign stable `doc_id` (ULID format).

**Acceptance criteria**
- Every document has non-null hash + doc_id.
- Hash collision handling exists (extremely rare path).
- Original file path is immutable after archive finalize.

## F3. Metadata Extraction
- Required fields: date, source, audience, doc type, title (nullable), summary_1_sentence.
- Optional fields: references, plan_phase, notes.
- Confidence scores per extracted field.

**Acceptance criteria**
- Required fields populated or flagged for review.
- Confidence < threshold moves record to Review Queue.
- Manual edits are versioned in metadata history.

## F4. Tagging & Taxonomy
- Controlled vocabulary with admin-editable taxonomy.
- Supports multi-tag and tag aliases.

**Acceptance criteria**
- Users can assign/update tags without breaking history.
- Duplicate tags are merged cleanly.
- Searches over tags return correct documents.

## F5. Conversion Pipeline
- Generate normalized derivatives: txt, md, searchable pdf (if source supports), docx (optional).
- Preserve conversion errors per derivative.

**Acceptance criteria**
- At least one readable derivative for supported formats.
- Failed derivative does not fail whole pipeline.
- Derivative links visible on document detail page.

## F6. Reference Linking
- Parse references from text/metadata (e.g., by date/source cues).
- Create document-to-document links with confidence.

**Acceptance criteria**
- Linked references visible in both directions.
- User can confirm/reject uncertain links.
- Reference graph updates immediately after confirmation.

## F7. Search & Retrieval
- Structured filters: date range, source, tags, topic, has_reference.
- Full-text search over normalized text.
- Sort: relevance, newest, oldest, source.

**Acceptance criteria**
- Common query returns in <= 5s for 50k documents (local machine baseline).
- Search results include key metadata and quick actions.
- Click-through opens detail page and selected file version.

## F8. Review Queue
- Queue for low-confidence metadata/links/conversion failures.
- Batch review mode.

**Acceptance criteria**
- Queue count visible on dashboard.
- Approve/edit actions write audit log entries.
- Resolved items exit queue immediately.

## F9. Auditability & Logs
- Persist pipeline runs, step outcomes, errors, timestamps, operator actions.

**Acceptance criteria**
- Every document has traceable pipeline history.
- Every manual metadata change is attributable + timestamped.
- Exportable diagnostics for debugging.

## F10. Backup/Export
- One-click export bundle: db snapshot + metadata sidecars + documents.

**Acceptance criteria**
- Export verifies checksums.
- Restore process documented and tested.
- Backup run status visible in UI.

## 9) Success Metrics
- 95%+ dedupe precision
- 90%+ metadata auto-fill without manual correction for clear documents
- <5s median retrieval on common filters
- <2% pipeline fatal failure rate
- 100% originals preserved with hash integrity

## 10) Constraints
- Local-first by default
- Offline-capable for core functions
- Deterministic file naming and schema versioning
- Human-in-the-loop for uncertain extraction

## 11) Risks & Mitigations
- Risk: taxonomy drift -> Mitigation: controlled vocabulary + aliasing
- Risk: conversion fidelity loss -> Mitigation: keep immutable original + side-by-side viewer
- Risk: model hallucination in metadata -> Mitigation: schema validation + confidence + review queue

## 12) Definition of Done (v1)
v1 is done when all in-scope features F1–F10 meet acceptance criteria, end-to-end workflow runs without manual CLI intervention, and export/restore round-trip passes integration tests.

## 13) Cross-References
- User navigation and flows: `APP_FLOW.md`
- Implementation dependencies and versions: `TECH_STACK.md`
- UI/UX consistency rules: `FRONTEND_GUIDELINES.md`
- Data model and API contracts: `BACKEND_STRUCTURE.md`
- Build order and milestone plan: `IMPLEMENTATION_PLAN.md`
- Session rules and constraints: `PERSISTANT.md`
# APP_FLOW.md

# LetterOps — App Flow

## 1) Screen Inventory (Routes)
- `/` Dashboard
- `/ingest` Ingestion Inbox (new/processing/failed)
- `/search` Search & Filters
- `/docs/:docId` Document Detail
- `/review` Review Queue
- `/graph` Reference Graph
- `/runs` Pipeline Runs
- `/runs/:runId` Pipeline Run Detail
- `/settings/general` General Settings
- `/settings/taxonomy` Tag Taxonomy
- `/settings/sources` Ingestion Sources
- `/settings/backups` Backup/Restore

## 2) Global Navigation
Top nav: Dashboard, Ingest, Search, Review, Graph, Runs, Settings  
Persistent badge: Review Queue count + Failed pipeline count.

## 3) Primary Flows

## Flow A: New Letter via Watched Directory
Trigger: file created in watched folder

1. System detects new file.
2. Create ingestion event + pipeline run.
3. Compute hash and dedupe check.
4. If duplicate:
   - Mark as duplicate event.
   - Link to existing doc.
   - End success path.
5. If new:
   - Store immutable original.
   - Extract metadata + confidence.
   - Generate derivatives.
   - Extract references and tag suggestions.
   - Index structured + full text.
6. If confidence below threshold:
   - Add to Review Queue.
7. Document appears in `/ingest` and searchable in `/search`.

Success: document indexed, retrievable, archived.  
Error path: step fails -> run status `partial_failed` or `failed`, visible in `/runs` and `/review`.

## Flow B: New Letter via Email Import (.eml)
Trigger: manual .eml drop or mailbox poll event

1. Parse attachment/body candidates.
2. For each candidate: run Flow A pipeline.
3. Store email provenance metadata (message-id, sender, received_at).

Decision points:
- No valid attachment -> mark as unsupported with reason.
- Multiple docs in one email -> separate document records.

## Flow C: Review Queue Resolution
Trigger: user opens `/review`

1. List items by type: metadata low confidence, unresolved references, conversion failures.
2. User opens item detail panel.
3. User approves/edit/rejects suggestion.
4. System writes change to audit log and metadata history.
5. Item exits queue if resolved.

Success: queue count decreases, document status updated.  
Error: validation fails -> keep item in queue with inline error hints.

## Flow D: Search and Re-access Filed Letter
Trigger: user opens `/search`

1. User enters query and optional filters (date/source/topic/tag/reference).
2. API returns ranked results.
3. User opens `/docs/:docId`.
4. Detail page shows:
   - metadata card
   - linked references
   - versions (pdf/txt/md/docx)
   - file location + provenance
5. User opens desired version or copies canonical file path.

Success: target letter opened in <=5s median.

## Flow E: “Current Letter References Prior Letter”
Trigger: in `/docs/:docId`, user sees reference section

1. Click a linked reference.
2. If linked doc exists -> navigate directly to referenced `/docs/:docId`.
3. If unresolved reference -> open “Resolve Reference” modal:
   - suggested matches
   - manual search fallback
4. User confirms match -> bidirectional link created.

Success: prior guidance re-accessed instantly.

## Flow F: Taxonomy Management
Trigger: `/settings/taxonomy`

1. Create/edit/archive tags and aliases.
2. Merge duplicate tags.
3. Reindex impacted docs in background.

Success: taxonomy remains clean and consistent.

## 4) Route-Level Error States
- 404 doc not found -> offer search fallback
- run step failure -> show failed stage + retry action
- conversion unavailable -> offer original file open
- DB unavailable -> read-only degraded mode banner

## 5) Empty States
- No documents: onboarding CTA to configure watched folder.
- No review items: “All caught up.”
- No search results: suggest clearing one filter at a time.

## 6) Cross-References
- Feature contract and acceptance: `PRD.md`
- API/DB behavior: `BACKEND_STRUCTURE.md`
- UI standards: `FRONTEND_GUIDELINES.md`
- Build sequence: `IMPLEMENTATION_PLAN.md`
# TECH_STACK.md

# LetterOps — Tech Stack (Pinned)

## 1) Runtime & Toolchain
- OS target: macOS/Linux (Windows supported)
- Node.js: `20.17.0`
- pnpm: `9.12.2`
- Python: `3.12.6`
- SQLite: `3.46.x` with FTS5 enabled
- Git: `2.46.x`

## 2) Monorepo Layout
- `apps/web` (Next.js frontend)
- `apps/api` (FastAPI backend)
- `apps/worker` (pipeline worker)
- `packages/shared` (shared schemas/types)
- `infra` (scripts, migrations, backup tooling)

## 3) Frontend
- Next.js: `14.2.5`
- React: `18.2.0`
- React DOM: `18.2.0`
- TypeScript: `5.5.4`
- Tailwind CSS: `3.4.10`
- PostCSS: `8.4.41`
- Autoprefixer: `10.4.20`
- TanStack Query: `5.56.2`
- Zod: `3.23.8`
- React Hook Form: `7.53.0`
- Axios: `1.7.7`
- Zustand: `4.5.4`
- Day.js: `1.11.13`
- ESLint: `9.10.0`
- Prettier: `3.3.3`
- Playwright: `1.47.0`

## 4) Backend API
- FastAPI: `0.115.0`
- Uvicorn: `0.30.6`
- Pydantic: `2.9.1`
- SQLAlchemy: `2.0.35`
- Alembic: `1.13.2`
- aiosqlite: `0.20.0`
- python-multipart: `0.0.9`
- python-jose: `3.3.0`
- passlib[bcrypt]: `1.7.4`
- structlog: `24.4.0`

## 5) Worker / Pipeline
- Celery: **not used in v1**
- APScheduler: `3.10.4`
- watchdog: `5.0.2`
- pypdf: `5.0.1`
- python-docx: `1.1.2`
- markdownify: `0.13.1`
- openai: `1.51.2` (optional assistive extraction)
- tenacity: `9.0.0`

## 6) Data & Search
- Primary DB: SQLite (local file)
- Full-text search: SQLite FTS5 virtual tables
- Embeddings/vector DB: **out of scope v1**

## 7) Testing & Quality
- pytest: `8.3.3`
- pytest-asyncio: `0.24.0`
- ruff: `0.6.8`
- black: `24.8.0`
- mypy: `1.11.2`
- pre-commit: `3.8.0`

## 8) Packaging / Deployment
- Docker: `24.x` (optional local containerization)
- docker-compose: `2.29.x` (optional)
- Systemd/launchd scripts for local worker process

## 9) Rules
- Lockfiles are mandatory (`pnpm-lock.yaml`, `requirements.lock`).
- No dependency upgrades without changelog entry and integration tests.
- No unpinned major versions.
- No additional framework adoption without PRD update.

## 10) Cross-References
- Feature requirements: `PRD.md`
- UI implementation constraints: `FRONTEND_GUIDELINES.md`
- API + DB contracts: `BACKEND_STRUCTURE.md`
- Build order: `IMPLEMENTATION_PLAN.md`
# FRONTEND_GUIDELINES.md

# LetterOps — Frontend Guidelines

## 1) Design Principles
- Calm, archival, low-noise interface.
- Prioritize scanability and retrieval speed.
- Consistency over novelty.
- Accessibility is non-negotiable.

## 2) Typography
- Primary font: `Inter`
- Monospace: `JetBrains Mono`
- Base size: `16px`
- Scale:
  - xs 12
  - sm 14
  - md 16
  - lg 18
  - xl 20
  - 2xl 24
  - 3xl 30

## 3) Color Tokens (Exact)
- `--bg`: `#0B1020`
- `--panel`: `#121A2B`
- `--panel-2`: `#18233A`
- `--text-primary`: `#E8EDF7`
- `--text-secondary`: `#A9B4CC`
- `--border`: `#2A3653`
- `--accent`: `#5EA1FF`
- `--accent-2`: `#7BC4FF`
- `--success`: `#2FB37A`
- `--warning`: `#F2B84B`
- `--error`: `#E05D6F`
- `--info`: `#72A7FF`

Light mode is out of scope v1 (single dark theme).

## 4) Spacing Scale (8pt system)
- `4, 8, 12, 16, 24, 32, 40, 48, 64`

## 5) Radius, Shadow, Border
- Radius:
  - sm `6px`
  - md `10px`
  - lg `14px`
- Border width: `1px` default
- Shadow:
  - card: `0 8px 24px rgba(0,0,0,0.28)`
  - modal: `0 16px 40px rgba(0,0,0,0.35)`

## 6) Layout
- Max content width: `1280px`
- Main grid:
  - desktop: 12 columns
  - tablet: 8 columns
  - mobile: 4 columns
- Page padding:
  - desktop `24px`
  - tablet `20px`
  - mobile `16px`

## 7) Breakpoints
- sm: `640px`
- md: `768px`
- lg: `1024px`
- xl: `1280px`
- 2xl: `1536px`

## 8) Component Rules

## Buttons
- Primary: accent bg, dark text, hover +6% brightness
- Secondary: panel-2 bg, border, text-primary
- Danger: error bg, white text
- Disabled: opacity 45%, no elevation

## Inputs
- Height: `40px`
- Border: `1px solid var(--border)`
- Focus ring: `2px solid #5EA1FF`
- Placeholder: text-secondary at 70%

## Cards
- Background: panel
- Border: border token
- Header/body/footer spacing: 16/16/12

## Tables
- Dense mode default
- Sticky header
- Row hover uses panel-2
- First column reserved for primary identifier (date/title)

## Status Chips
- success/warning/error/info color tokens
- always include icon + text label

## 9) Iconography
- Library: Lucide
- 16px default, 20px in nav
- Avoid decorative-only icons

## 10) Motion
- Keep transitions <= 150ms
- No parallax or excessive animation
- Respect reduced-motion preference

## 11) Accessibility
- WCAG AA contrast minimum
- Full keyboard navigation for core flows
- Visible focus states everywhere
- ARIA labels for icon-only buttons
- Error messages linked to inputs

## 12) Screen-Specific Guidelines
- Dashboard: KPI cards + queue summary + recent runs
- Search: left filter rail + right results list
- Document detail: metadata sidebar + content pane + references pane
- Review queue: batch actions fixed at top

## 13) Forbidden UI Patterns
- No inline random hex colors
- No custom spacing outside token scale
- No hidden critical actions in kebab-only menus
- No modal for core reading flow

## 14) Cross-References
- Functional expectations: `PRD.md`
- Route behavior: `APP_FLOW.md`
- API field shapes: `BACKEND_STRUCTURE.md`
# BACKEND_STRUCTURE.md

# LetterOps — Backend Structure

## 1) Architecture
- API: FastAPI (`apps/api`)
- Worker: Python worker with watchdog + scheduled tasks (`apps/worker`)
- DB: SQLite + FTS5
- File store: local filesystem under `/data`

## 2) Data Model (SQLite DDL)

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('owner','editor','viewer')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN ('watch_folder','eml_import','manual_upload')),
  name TEXT NOT NULL,
  config_json TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE documents (
  id TEXT PRIMARY KEY,                      -- ULID
  sha256 TEXT NOT NULL UNIQUE,
  canonical_title TEXT,
  source_name TEXT,                         -- e.g., Universal House of Justice
  audience TEXT,
  document_date TEXT,                       -- ISO date yyyy-mm-dd
  document_type TEXT,                       -- message, letter, update, etc
  summary_one_sentence TEXT,
  confidence_overall REAL NOT NULL DEFAULT 0.0,
  status TEXT NOT NULL CHECK(status IN ('ingested','indexed','needs_review','archived','failed')),
  archive_path TEXT NOT NULL,               -- immutable original path
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE document_files (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  file_kind TEXT NOT NULL CHECK(file_kind IN ('original','pdf','txt','md','docx')),
  path TEXT NOT NULL,
  mime_type TEXT,
  bytes INTEGER,
  checksum_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(document_id, file_kind)
);

CREATE TABLE document_metadata_versions (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  version_no INTEGER NOT NULL,
  metadata_json TEXT NOT NULL,
  edited_by_user_id TEXT REFERENCES users(id),
  edit_reason TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(document_id, version_no)
);

CREATE TABLE tags (
  id TEXT PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,                 -- normalized key, e.g. "growth"
  label TEXT NOT NULL,                      -- display label
  parent_tag_id TEXT REFERENCES tags(id),
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE tag_aliases (
  id TEXT PRIMARY KEY,
  tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  alias TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE document_tags (
  document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  confidence REAL NOT NULL DEFAULT 1.0,
  assigned_by TEXT NOT NULL CHECK(assigned_by IN ('system','user')),
  created_at TEXT NOT NULL,
  PRIMARY KEY (document_id, tag_id)
);

CREATE TABLE document_links (
  id TEXT PRIMARY KEY,
  from_document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  to_document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  link_type TEXT NOT NULL CHECK(link_type IN ('references','clarifies','supersedes','related')),
  confidence REAL NOT NULL DEFAULT 1.0,
  state TEXT NOT NULL CHECK(state IN ('suggested','confirmed','rejected')),
  created_by TEXT NOT NULL CHECK(created_by IN ('system','user')),
  created_at TEXT NOT NULL,
  UNIQUE(from_document_id, to_document_id, link_type)
);

CREATE TABLE ingestion_events (
  id TEXT PRIMARY KEY,
  source_id TEXT REFERENCES sources(id),
  trigger_type TEXT NOT NULL CHECK(trigger_type IN ('file_watch','eml_import','manual_upload','retry')),
  payload_json TEXT NOT NULL,
  event_time TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('received','processed','failed'))
);

CREATE TABLE pipeline_runs (
  id TEXT PRIMARY KEY,
  ingestion_event_id TEXT REFERENCES ingestion_events(id),
  document_id TEXT REFERENCES documents(id),
  status TEXT NOT NULL CHECK(status IN ('running','success','partial_failed','failed')),
  started_at TEXT NOT NULL,
  ended_at TEXT,
  error_summary TEXT
);

CREATE TABLE pipeline_steps (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  step_name TEXT NOT NULL,                  -- hash, dedupe, extract, convert, index, link
  status TEXT NOT NULL CHECK(status IN ('running','success','failed','skipped')),
  started_at TEXT NOT NULL,
  ended_at TEXT,
  logs TEXT
);

CREATE TABLE audit_events (
  id TEXT PRIMARY KEY,
  actor_user_id TEXT REFERENCES users(id),
  action TEXT NOT NULL,
  object_type TEXT NOT NULL,
  object_id TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT,
  created_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE document_fts USING fts5(
  document_id UNINDEXED,
  title,
  summary,
  full_text,
  source_name,
  tags
);

CREATE INDEX idx_documents_date ON documents(document_date);
CREATE INDEX idx_documents_source ON documents(source_name);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_document_links_from ON document_links(from_document_id);
CREATE INDEX idx_document_links_to ON document_links(to_document_id);
3) File Storage Rules
Root: /data

Immutable original:

/data/archive/originals/YYYY/MM/DD/{doc_id}/{original_filename}

Derivatives:

/data/archive/derived/{doc_id}/{doc_id}.{ext}

Metadata sidecars:

/data/metadata/{doc_id}/metadata.v{n}.json

Run artifacts/logs:

/data/runs/{run_id}/...

Rules:

Never mutate original file bytes.

Any metadata edit creates new metadata version.

Any conversion rewrite creates new derivative checksum.

4) Authentication & Authorization
v1 modes:

single_user (default): one owner account, local JWT auth.

team_mode (optional): owner/editor/viewer roles.

JWT in HttpOnly cookie.

Access token TTL: 8h

Refresh token TTL: 30d

Password hashing: bcrypt

Permissions:

owner: full access

editor: ingest, review, edit metadata/tags

viewer: read/search only

5) API Contracts (REST, /api/v1)
Auth
POST /auth/login

POST /auth/logout

GET /auth/me

Documents
GET /documents (filters: q, date_from, date_to, source, tags, status, has_reference)

GET /documents/{id}

POST /documents/upload

PATCH /documents/{id}/metadata

GET /documents/{id}/files

GET /documents/{id}/links

POST /documents/{id}/links/confirm

POST /documents/{id}/links/reject

Review
GET /review/items

POST /review/items/{id}/resolve

POST /review/items/{id}/reopen

Pipeline
GET /runs

GET /runs/{id}

POST /runs/{id}/retry

Taxonomy
GET /tags

POST /tags

PATCH /tags/{id}

POST /tags/merge

POST /tags/{id}/aliases

Backup
POST /backup/export

POST /backup/restore

GET /backup/history

Response envelope:

{
  "data": {},
  "error": null,
  "meta": {}
}
6) Edge Cases & Expected Behavior
Duplicate hash: return existing document_id, create duplicate ingestion event

Missing date: set document_date = null, status needs_review

Ambiguous source: store suggestion + confidence, queue review

Conversion fail for one type: run partial_failed, keep other outputs

Link suggestion no match: state suggested unresolved

DB locked: retry with backoff up to 3 attempts, then fail run

7) Cross-References
Feature contract: PRD.md

Route behavior: APP_FLOW.md

Dependency lock: TECH_STACK.md

Build steps: IMPLEMENTATION_PLAN.md


---

```markdown
# IMPLEMENTATION_PLAN.md

# LetterOps — Implementation Plan

## Phase 0: Repo + Governance
### 0.1 Initialize repository
- Create monorepo structure per `TECH_STACK.md`
- Add root docs from this canonical set
- Add `LICENSE`, `README.md`, `.editorconfig`

### 0.2 Add quality gates
- Setup pre-commit (ruff, black, eslint, prettier, type checks)
- Configure CI (lint, unit tests, build)

### 0.3 Define branching strategy
- `main` protected
- feature branches: `feat/*`
- fix branches: `fix/*`

## Phase 1: Backend Foundation
### 1.1 Bootstrap FastAPI app
- health endpoint
- config loader
- structured logging

### 1.2 Implement DB schema
- Add SQLAlchemy models matching `BACKEND_STRUCTURE.md`
- Add Alembic migrations
- Seed default owner + tag taxonomy baseline

### 1.3 Auth module
- login/logout/me
- JWT cookies + bcrypt
- role guards

## Phase 2: File & Pipeline Core
### 2.1 Storage service
- deterministic path builders
- immutable original write
- checksum utility

### 2.2 Ingestion events
- watched-folder trigger (watchdog)
- manual upload endpoint
- .eml parser ingestion adapter

### 2.3 Pipeline runner
- stages: hash -> dedupe -> extract -> convert -> index -> link
- run/step persistence with statuses
- retry support

## Phase 3: Metadata + Conversion
### 3.1 Deterministic extraction
- parse date/source/title where explicit
- fallback extraction heuristics

### 3.2 Assistive LLM extraction (optional)
- enforce strict JSON schema output
- confidence per field
- fallback to deterministic parser on failure

### 3.3 Derivative generation
- txt + md required
- pdf/docx optional
- partial failure behavior

## Phase 4: Search & Linking
### 4.1 FTS index
- build `document_fts`
- trigger updates on metadata/derivative updates

### 4.2 Structured search endpoint
- filters + sorting + pagination

### 4.3 Reference linker
- suggestion engine by date/source cues
- persist `document_links` suggested state

## Phase 5: Frontend App
### 5.1 Next.js scaffolding
- global layout + nav + route guards
- theme tokens from `FRONTEND_GUIDELINES.md`

### 5.2 Build routes
- `/`, `/ingest`, `/search`, `/docs/:id`, `/review`, `/graph`, `/runs`, `/settings/*`

### 5.3 Document detail UI
- metadata panel
- file version links
- references panel with resolve actions

### 5.4 Review queue UI
- batch accept/edit/reject
- inline validation and audit trail link

## Phase 6: Observability + Audit
### 6.1 Pipeline run dashboard
- status counters, failure drill-down

### 6.2 Audit log views
- user actions + metadata diff viewer

### 6.3 Error handling
- API error envelope standardization
- frontend boundary components

## Phase 7: Backup/Restore
### 7.1 Export bundle
- DB snapshot + files + metadata + manifest checksums

### 7.2 Restore flow
- validation before import
- dry-run mode

### 7.3 Disaster recovery test
- clean environment restore test in CI

## Phase 8: Hardening & Release
### 8.1 Performance test
- 50k doc test fixture, median query latency target

### 8.2 Security checks
- dependency audit
- auth/session tests

### 8.3 Release checklist
- all PRD acceptance criteria validated
- docs updated
- `progress.txt` updated with release notes

## Milestones
- M1: ingest + archive + search baseline
- M2: review queue + reference links
- M3: backup/restore + hardening
- M4: v1 release candidate

## Definition of Ready (per task)
- Task references exact section in PRD/Flow/Backend docs
- Acceptance criteria testable
- Dependencies identified

## Definition of Done (per task)
- Code complete + tests
- UI aligned to frontend guidelines
- Docs updated
- `progress.txt` updated

## Cross-References
- Scope: `PRD.md`
- Flows: `APP_FLOW.md`
- Versions: `TECH_STACK.md`
- Data/API: `BACKEND_STRUCTURE.md`
- Session constraints: `PERSISTANT.md`
# PERSISTANT.md

# LetterOps — Persistent Operating Rules (Read First Every Session)

## 1) Session Boot Rules (Mandatory)
Before writing code:
1. Read `PERSISTANT.md`
2. Read `progress.txt`
3. Read relevant sections of:
   - `PRD.md`
   - `APP_FLOW.md`
   - `TECH_STACK.md`
   - `FRONTEND_GUIDELINES.md`
   - `BACKEND_STRUCTURE.md`
   - `IMPLEMENTATION_PLAN.md`

Do not start implementation before this sequence.

## 2) Source of Truth Priority
1. `PRD.md` (what to build)
2. `BACKEND_STRUCTURE.md` (data/API contracts)
3. `FRONTEND_GUIDELINES.md` (visual/UX consistency)
4. `APP_FLOW.md` (user journeys)
5. `TECH_STACK.md` (versions/deps)
6. `IMPLEMENTATION_PLAN.md` (build order)
7. `progress.txt` (current state)

If conflicts exist, open issue + propose patch to canonical docs first.

## 3) Allowed / Forbidden

## Allowed
- Implement only items in PRD scope
- Add tests and docs with every feature
- Refactor if behavior unchanged and tests pass
- Add migration scripts for schema changes

## Forbidden
- Unpinned dependencies
- Silent schema changes without migration
- UI styles outside design tokens
- Skipping audit logs on manual edits
- Mutating immutable original files
- Introducing new frameworks without TECH_STACK update

## 4) Coding Patterns
- Prefer small pure functions and explicit types
- Idempotent pipeline steps
- Fail closed with clear error messages
- Structured logs only (no ad hoc prints)
- API responses use standard envelope

## 5) Naming Conventions
- `doc_id`: ULID
- snake_case in backend/Python
- camelCase in frontend/TypeScript
- File names:
  - backend: `*_service.py`, `*_router.py`, `*_repo.py`
  - frontend: `ComponentName.tsx`, `useFeatureHook.ts`

## 6) Testing Requirements
- Unit tests for new services/utilities
- Integration tests for API endpoints
- E2E smoke tests for core flows:
  - ingest
  - search
  - review resolve
  - open referenced letter
- No merge to main if tests fail

## 7) Quality Gates
- lint, format, typecheck, test must pass
- migrations reversible where feasible
- update `progress.txt` after every completed feature

## 8) Human-in-the-Loop Rules
- Low-confidence extraction must enter review queue
- Never auto-confirm uncertain document links
- Preserve metadata edit history

## 9) Security & Data Handling
- Store secrets in `.env` (never commit)
- Hash and verify backup artifacts
- Principle of least privilege for roles

## 10) Session Completion Checklist
- [ ] Code + tests green
- [ ] Docs updated if behavior changed
- [ ] `progress.txt` updated (done/in-progress/next)
- [ ] Known issues recorded

# progress.txt

Project: LetterOps
Last Updated: YYYY-MM-DD HH:MM (local)

========================================
CURRENT STATUS SNAPSHOT
========================================
Phase:
Branch:
Overall Progress: XX%

Done:
- [ ] ...

In Progress:
- [ ] ...

Next:
- [ ] ...
- [ ] ...
- [ ] ...

Blocked:
- [ ] (issue, blocker, owner, next action)

========================================
FEATURE LOG (append-only)
========================================
[YYYY-MM-DD] Feature: <name>
- Scope reference: PRD.md §F#
- What was built:
  - ...
- Tests added/updated:
  - ...
- Result:
  - PASS/FAIL
- Known gaps:
  - ...
- Follow-up tasks:
  - ...

[YYYY-MM-DD] Feature: <name>
- Scope reference: ...
- What was built:
  - ...
- Tests added/updated:
  - ...
- Result:
  - ...
- Known gaps:
  - ...
- Follow-up tasks:
  - ...

========================================
PIPELINE HEALTH
========================================
Latest run IDs:
- run_id:
- run_id:

Failure patterns observed:
- ...

Reliability notes:
- ...

========================================
TECH DEBT / IMPROVEMENTS
========================================
- [ ] ...
- [ ] ...

========================================
RELEASE CHECKLIST (v1)
========================================
- [ ] All PRD acceptance criteria validated
- [ ] Backup/restore round-trip tested
- [ ] Search latency target met
- [ ] Documentation complete
- [ ] Security checks complete