# apps/web

Phase 5 frontend shell for LetterOps search UX.

## Run locally

From repo root:

```bash
python3 -m http.server 3000 --directory apps/web
```

Open `http://127.0.0.1:3000` and point API base to your running backend, usually:

- `http://127.0.0.1:8000/api/v1`

## Current scope

- Login via `/auth/login` (cookie session).
- Search via `/search` with `query` + `limit`.
- Render answer summary, confidence score/label, citations, and ranked hits.

This is intentionally lightweight so UX iteration can proceed before a full Next.js setup.
