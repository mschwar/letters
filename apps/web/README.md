# apps/web

Next.js App Router frontend for LetterOps Phase 5.

## Routes

- `/dashboard`: sign-in + search execution + ranked evidence.
- `/review`: quality checks for confidence/citation completeness.
- `/graph`: query/citation/result relationship graph.

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

Vercel or any Node host that supports Next.js standalone server:

```bash
npm run build
npm run start
```
