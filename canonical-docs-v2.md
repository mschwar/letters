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
- avoid duplicate/manual processing toil. +Kept: GPT's core; added Gemini's "thematic correlation" to problem list.

## 4) Product Goals

1. Ingest all new letters with deterministic metadata capture.
2. Preserve original files immutably and generate standardized derivatives.
3. Provide sub-5-second retrieval for common queries (structured + optional semantic).
4. Surface references between letters as first-class links.
5. Keep human review where model confidence is low. +Revised: Added semantic from Gemini for efficiency.

## 5) Non-Goals (Explicitly Out of Scope for v1)

- No autonomous legal/theological interpretation.
- No public sharing or publishing portal.
- No mobile-native app.
- No full OCR pipeline for poor scans (OCR only optional helper if needed).
- No multi-tenant enterprise RBAC beyond basic owner/editor roles.
- No cloud dependencies (e.g., no external APIs for LLM; local only). +Revised: Discarded Gemini's mobile out-of-scope (redundant); added no-cloud to enforce local-first.

## 6) In Scope (v1)

- Email/file-triggered ingestion pipeline
- Hashing, dedupe, provenance tracking
- Metadata extraction + confidence scoring
- Tag taxonomy + controlled vocabulary
- Reference extraction/linking
- Search (structured + full text + optional semantic RAG)
- Archive browser and document detail views
- Pipeline run logs and error handling
- Export/backup of DB + files + metadata sidecars +Revised: Kept GPT's list; added Gemini's RAG as optional (local ChromaDB in Git dir).

## 7) User Stories

1. As a user, when a new letter arrives, I want it automatically indexed and filed so I don’t do repetitive manual work.
2. As a user, when a current letter references an earlier one, I want one-click retrieval of that prior letter.
3. As a user, I want to trust the archive: originals immutable, provenance visible, duplicates detected.
4. As a user, I want low-confidence metadata flagged for review before finalization.
5. As a user, I want to search by date/source/topic/tags/reference and open preferred format (pdf/txt/md/docx). +Kept: GPT's; added Gemini's implied "semantic query" story: 6. As a user, I want natural-language search (e.g., "guidance on funds") with cited sources.

## 8) Feature Requirements & Acceptance Criteria

[Kept GPT's F1-F10 mostly intact; revised F7 to include semantic: -Structured filters only +Structured filters + optional RAG for natural queries. Added criteria for semantic: Results include AI summary + sources, local-only processing.]

## 9) Success Metrics

- 95%+ dedupe precision
- 90%+ metadata auto-fill without manual correction for clear documents
- <5s median retrieval on common filters (structured); <10s for semantic
- <2% pipeline fatal failure rate
- 100% originals preserved with hash integrity +Revised: Added semantic latency from Gemini.

## 10) Constraints

- Local-first by default
- Offline-capable for core functions
- Deterministic file naming and schema versioning
- Human-in-the-loop for uncertain extraction
- Git repo for entire system (DB file versioned) +Revised: Added explicit Git constraint.

## 11) Risks & Mitigations

[Kept GPT's; added from Gemini: Risk: LLM dependency -> Mitigation: Optional local Ollama, fallback to deterministic parsing.]

## 12) Definition of Done (v1)

[Kept GPT's; added: Semantic search tested with local vectors.]

## 13) Cross-References

[Kept GPT's; added Gemini's BACKEND_STRUCTURE.md for schema inspiration.]

---

# APP_FLOW.md (Revised v2)

[Kept GPT's structure: Screen Inventory, Global Nav, Flows A-F. Revised Flow D to include semantic search from Gemini: +User types natural query -> System vectorizes, queries DB, synthesizes answer with sources. Added Flow G: Backup/Commit to Git (post-ingestion commit for versioning).]

---

# TECH_STACK.md (Revised v2)

## 1) Runtime & Toolchain

- OS target: macOS/Linux (Windows supported)
- Node.js: 20.17.0
- pnpm: 9.12.2
- Python: 3.12.6
- SQLite: 3.46.x with FTS5 enabled
- Git: 2.46.x +Kept GPT's; added Gemini's ChromaDB: 0.4.x (optional for vectors, persisted in Git dir).

## 2) Monorepo Layout

- apps/web (Next.js frontend)
- apps/api (FastAPI backend, simplified for local)
- apps/worker (pipeline worker)
- packages/shared (shared schemas/types)
- infra (scripts, migrations, backup tooling)
- data/db.sqlite (versioned in Git) +Revised: Simplified GPT's; added Gemini's /scripts for ETL.

[Rest kept similar; revised backend to optional local LLM (Ollama) instead of OpenAI.]

---

# FRONTEND_GUIDELINES.md (Revised v2)

[Kept GPT's dark theme; revised colors to blend with Gemini's serene palette: -GPT accents +Gemini indigo/amber for dignity. Added Gemini's component rules for cards/tags.]

---

# BACKEND_STRUCTURE.md (Revised v2)

## 1) Architecture

- API: FastAPI (apps/api)
- Worker: Python worker with watchdog + scheduled tasks (apps/worker)
- DB: SQLite + FTS5 (file in Git)
- File store: local filesystem under /data (in Git)
- Optional Vectors: ChromaDB in /data/vectors (for semantic) +Revised: Kept GPT's; added Gemini's vectors as optional.

## 2) Data Model (SQLite DDL)

[Kept GPT's schema; simplified users to single-user (discard team auth for v1). Added Gemini's frontmatter fields to metadata_json.]

[Kept file storage, auth (simplified), API contracts; added /api/search for RAG from Gemini.]

---

# IMPLEMENTATION_PLAN.md (Revised v2)

[Kept GPT's phases; added Gemini's Phase 4: Intelligence (RAG) between GPT's 4 and 5. Revised Phase 0 to include Git init explicitly. Updated milestones to include semantic.]

---

# PERSISTANT.md (Revised v2)

[Kept GPT's rules; added Gemini's operational rules: +Type safety (no any), +Data integrity (files as truth). Revised forbidden: +No cloud LLMs.]

---

# progress.txt (Revised v2)

Project: LetterOps Last Updated: 2026-02-07 18:23 (CST)

# ======================================== CURRENT STATUS SNAPSHOT

Phase: 0 (Repo Setup) Branch: main Overall Progress: 0%

Done:

- Canonical docs reviewed and merged.

In Progress:

- Phase 0: Initialize repo.

Next:

- Phase 1: Backend Foundation.
- Implement ingestion script.
- Test Git-versioned DB.

Blocked:

- None.