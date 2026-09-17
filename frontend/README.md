# Mentora Frontend

Next.js 14 (App Router) + TypeScript port of the original static HTML mockups. See
`docs/phases/MENTORA_Phase1_Frontend_Documentation.md` for the full technical
reference (project structure, page-by-page breakdown, forms/fields inventory, and
the API contract the FastAPI backend needs to implement).

## Running locally

```bash
npm install
npm run dev          # http://localhost:3000, hot reload
# or for a lower-RAM daily-use mode:
npm run build && npm run start
```

No backend calls are wired up yet — every page renders static/mock data. Once the
FastAPI backend exists, set `NEXT_PUBLIC_API_URL` in a `.env.local` file (see
Section 10 of the doc above) and start wiring `fetch()` calls in per the checklist
in Section 12.
