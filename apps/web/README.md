# apps/web

Next.js App Router frontend for LetterOps Phase 5.

## Routes

- `/dashboard`: sign-in + search execution + ranked evidence (SSR when query params are present).
- `/review`: quality checks for confidence/citation completeness.
- `/graph`: query/citation/result relationship graph.

## Search SSR behavior

- Dashboard search state is URL-driven (`/dashboard?q=...&limit=...&sort=...`).
- When `q` is present, the page performs server-side search and renders results on first load.
- Request cookies are forwarded to the API for authenticated SSR retrieval.

## Local development

From `apps/web`:

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

## Build and run

From `apps/web`:

```bash
npm run build
npm run start
```

CI build mode:

```bash
npm run build:ci
```

## E2E tests (Playwright)

From `apps/web`:

```bash
npm run test:e2e
```

If browser binaries are not installed yet:

```bash
PLAYWRIGHT_BROWSERS_PATH=./.playwright-browsers npx playwright install chromium
```

## Environment

- `NEXT_PUBLIC_API_BASE` (optional)
- Default: `http://127.0.0.1:8000/api/v1`

## Deploy

Local production server:

```bash
npm ci
npm run build
npm run start
```

Vercel:

```bash
npm run deploy:vercel
```

`apps/web/vercel.json` defines install/build commands for hosted deployments.
