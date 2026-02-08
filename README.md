# LetterOps

Local-first document intelligence system for managing Bahá’í letters. See `canonical-docs-v2.md` for the authoritative PRD, flows, tech stack, and operating rules.

## Monorepo Layout
- `apps/web`: web UI shell (Phase 5)
- `apps/api`: FastAPI backend
- `apps/worker`: local ingestion worker
- `packages/shared`: shared schemas/types
- `infra`: migrations, scripts, backup tooling
- `data/db.sqlite`: versioned SQLite database

## Web UX Shell (Phase 5)
- Current Phase 5 UI is a lightweight shell at `apps/web` for login + search + citations.
- Run with `python3 -m http.server 3000 --directory apps/web` and open `http://127.0.0.1:3000`.
- API base defaults to `http://127.0.0.1:8000/api/v1`.

## Quick Start (Backend)
1. Create a virtualenv and install dependencies from `apps/api/requirements.txt`.
2. Set env vars in `.env` (see `.env.example` if present).
3. Run migrations using Alembic.
4. Start the API with `uvicorn app.main:app --reload` from `apps/api`.

## UHJ Scraping Utility
- Script: `infra/scripts/scrape_uhj_messages.py`
- Purpose: scrape UHJ messages index and save each message as markdown with frontmatter + content hash.
- Dry run example:
  - `.venv/bin/python infra/scripts/scrape_uhj_messages.py --dry-run --max-items 10`
- Pull real files:
  - `make scrape-uhj`
- Output path default:
  - `data/samples/uhj_messages_md`
