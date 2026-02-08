# BACKEND_STRUCTURE.md

Status: canonical summary + auto-generated schema sections. Source of truth: canonical-docs-v2.md.

## Architecture (Manual)
- API: FastAPI (apps/api)
- Worker: Python worker (apps/worker)
- DB: SQLite + FTS5 (data/db.sqlite)
- File store: data/archive (originals + derived)

## Data Model (Auto)
<!-- DOC-AGENT:START schema -->
### users
- id (String, PK)
- email (String, unique, not null)
- password_hash (String, not null)
- role (String, not null)
- created_at (Text, not null)
- updated_at (Text, not null)

### sources
- id (String, PK)
- kind (String, not null)
- name (String, not null)
- config_json (Text, not null)
- is_active (Integer, not null)
- created_at (Text, not null)
- updated_at (Text, not null)

### documents
- id (String, PK)
- sha256 (String, not null)
- canonical_title (String)
- source_name (String)
- audience (String)
- document_date (String)
- document_type (String)
- summary_one_sentence (Text)
- confidence_overall (Float, not null)
- status (String, not null)
- archive_path (Text, not null)
- created_at (Text, not null)
- updated_at (Text, not null)

### document_files
- id (String, PK)
- document_id (String, FK documents.id, not null)
- file_kind (String, not null)
- path (Text, not null)
- mime_type (String)
- bytes (Integer)
- checksum_sha256 (String, not null)
- created_at (Text, not null)

### document_metadata_versions
- id (String, PK)
- document_id (String, FK documents.id, not null)
- version_no (Integer, not null)
- metadata_json (Text, not null)
- edited_by_user_id (String, FK users.id)
- edit_reason (Text)
- created_at (Text, not null)

### tags
- id (String, PK)
- key (String, unique, not null)
- label (String, not null)
- parent_tag_id (String, FK tags.id)
- is_active (Integer, not null)
- created_at (Text, not null)
- updated_at (Text, not null)

### tag_aliases
- id (String, PK)
- tag_id (String, FK tags.id, not null)
- alias (String, unique, not null)
- created_at (Text, not null)

### document_tags
- document_id (String, PK, FK documents.id)
- tag_id (String, PK, FK tags.id)
- confidence (Float, not null)
- assigned_by (String, not null)
- created_at (Text, not null)

### document_links
- id (String, PK)
- from_document_id (String, FK documents.id, not null)
- to_document_id (String, FK documents.id, not null)
- link_type (String, not null)
- confidence (Float, not null)
- state (String, not null)
- created_by (String, not null)
- created_at (Text, not null)

### ingestion_events
- id (String, PK)
- source_id (String, FK sources.id)
- trigger_type (String, not null)
- payload_json (Text, not null)
- event_time (Text, not null)
- status (String, not null)

### pipeline_runs
- id (String, PK)
- ingestion_event_id (String, FK ingestion_events.id)
- document_id (String, FK documents.id)
- status (String, not null)
- started_at (Text, not null)
- ended_at (Text)
- error_summary (Text)

### pipeline_steps
- id (String, PK)
- run_id (String, FK pipeline_runs.id, not null)
- step_name (String, not null)
- status (String, not null)
- started_at (Text, not null)
- ended_at (Text)
- logs (Text)

### audit_events
- id (String, PK)
- actor_user_id (String, FK users.id)
- action (String, not null)
- object_type (String, not null)
- object_id (String, not null)
- before_json (Text)
- after_json (Text)
- created_at (Text, not null)
<!-- DOC-AGENT:END schema -->

## Cross-References
<!-- DOC-AGENT:START xrefs -->
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
- [TECH_STACK.md](TECH_STACK.md)
- [PERSISTANT.md](PERSISTANT.md)
- [DOC_AGENT.md](DOC_AGENT.md)
- [DOC_INDEX.md](DOC_INDEX.md)
- [canonical-docs-v2.md](canonical-docs-v2.md)
- [progress.txt](progress.txt)
<!-- DOC-AGENT:END xrefs -->
