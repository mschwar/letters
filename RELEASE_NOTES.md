# Release Notes

## v1.0.1 (2026-02-08)

Post-`v1.0.0` stabilization and frontend productionization updates on `main`.

### Highlights
- Migrated `apps/web` from static shell to Next.js App Router with production build/start flow.
- Added full phase routes:
  - `/dashboard` (auth + retrieval controls + answer/citations/results)
  - `/review` (confidence and citation-quality checks)
  - `/graph` (query-to-citation/result relationship view)
- Added richer global UI shell/theme and cross-route search-state persistence.
- Removed legacy static web files (`index.html`, `app.js`, `styles.css`).
- Upgraded frontend to patched Next.js (`16.1.6`) and added lint/typecheck/build validation.
- Added Playwright E2E coverage for dashboard/review/graph route flows.
- Added GitHub Actions CI workflow:
  - backend pytest
  - web build/lint/typecheck
  - Playwright browser install + E2E run

### Verification
- Backend tests: `17 passed`.
- Web checks: `npm run build`, `npm run lint`, `npm run typecheck` passing locally.
- E2E tests expanded and discoverable (`7 tests` across core flows); full browser execution in this sandbox is network-limited, but CI runs install + execution on runner.

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
