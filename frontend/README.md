# Mentora Frontend

Next.js 16 (App Router) + TypeScript port of the original static HTML mockups —
upgraded 2026-11-11 from 14.2.35 (fixed its flagged dependency vulnerabilities;
see that date's commit for the migration notes). See
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

Wired to the real FastAPI backend (Phase 2) — set `NEXT_PUBLIC_API_URL` in
`.env.local` (see Section 10 of the doc above) and start the backend first.
Every page calls real endpoints; see `docs/phases/MENTORA_Phase2_Frontend_Backend_Wiring.md`
for how the auth/proxy plumbing works.

This was built against Phase 2's original mock backend response shapes.
Phases 6-7 later changed several real endpoint shapes without the frontend
being revisited — a 2026-11-10 audit (see the repo's git log for that date)
found and fixed the resulting drift (stuck-loading bugs, a few crashes on
real responses, two missing required params). If something still looks
wrong against a specific endpoint, check that endpoint's actual response
shape in `docs/openapi.json` against `lib/types.ts` first — that mismatch
is the most common cause.
