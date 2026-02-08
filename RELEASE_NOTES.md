# Release Notes

## v1.0.0 (2026-02-08)

Initial baseline release of LetterOps as a local-first document intelligence system for letter archives.

### Highlights
- Established monorepo foundation and canonical documentation alignment.
- Shipped FastAPI backend with auth scaffold, health endpoint, and migration-backed SQLite schema.
- Built deterministic ingestion pipeline:
  - immutable original archiving
  - hash + dedupe
  - extraction and derivative generation (`txt`/`md`)
  - FTS indexing
  - run/step tracking
- Added linking and tagging persistence into pipeline flow.
- Added `/api/v1/search` retrieval endpoint with:
  - answer synthesis
  - confidence scoring
  - richer citation formatting
  - optional vector retrieval (Chroma)
  - hybrid ranking (FTS + vector fusion)
- Added judged-query evaluation harness and enforced search quality gate in automation.
- Reduced search tail latency with retriever caching and warm-up.
- Added release hardening checks:
  - backup/restore roundtrip verification
  - dependency integrity check
  - vulnerability audit check

### Quality and Performance Snapshot
- Test suite: `16 passed`.
- Search gate: `hit_rate@k=0.821`, `MRR=0.804`, `p95=60.121ms`, `no_hit_accuracy=1.0`.
- Release check: PASS (`verify`, `search-gate`, `backup-roundtrip`, `security-check`).

### Security and Dependency Updates
- Upgraded:
  - `fastapi` to `0.121.0` (and `starlette` to `0.49.3`)
  - `python-multipart` to `0.0.22`
  - `python-jose` to `3.4.0`
  - `pypdf` to `6.6.2`
  - `markdownify` to `0.14.1`
- Upgraded venv `pip` to `26.0.1`.
- One unpatched advisory is explicitly ignored in automation:
  - `ecdsa` `CVE-2024-23342` (no published fix version at release time).
