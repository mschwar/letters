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
