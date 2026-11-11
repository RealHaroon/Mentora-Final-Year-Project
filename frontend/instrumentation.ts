export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;

  // 2026-11-11: the proxy route (app/api/proxy/[...path]/route.ts) forwards
  // every browser request to FastAPI with plain fetch(). Node's global fetch
  // is undici under the hood, and undici's default Agent enforces its own
  // headersTimeout (independent of any AbortSignal a caller passes) — found
  // failing live as `UND_ERR_HEADERS_TIMEOUT` on /exam/mcq specifically,
  // which calls M2 (the local FLAN-T5 question generator) and can
  // legitimately take minutes under the real memory contention this
  // project's tight 8GB RAM budget causes (see Phase 8's Locust findings
  // and docs/phase10/testing_results_summary.md). Every other backend call
  // finishes in well under a second, so raising this globally has no
  // downside for them.
  const { Agent, setGlobalDispatcher } = await import("undici");
  setGlobalDispatcher(new Agent({ headersTimeout: 10 * 60_000, bodyTimeout: 10 * 60_000 }));
}
