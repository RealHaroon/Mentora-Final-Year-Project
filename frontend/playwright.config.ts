import { defineConfig, devices } from "@playwright/test";

// Phase 2 §8's manual click-through checklist, automated. Requires the real
// backend AND frontend both already running (npm run dev / start_backend.sh,
// or scripts/start_all.sh) — these tests exercise the real ML models and RAG
// pipeline, not mocks, so there's nothing for webServer to safely auto-start
// (an auto-started backend here wouldn't have GROQ_API_KEY/model artifacts
// guaranteed set up the way a developer's own already-running instance does).
//
// M2 (question generator) can take 60-90s under load (Phase 8's Locust
// findings) and Groq-backed RAG calls add a few seconds each — the default
// 30s test timeout is too tight for this app's real, disclosed latency
// profile, not a sign something's hanging.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // shares one backend instance + the question_bank_fallback's remaining-question counter; parallel runs would race each other
  retries: 0,
  workers: 1,
  // M2 (question generator) idle-unloads after 5 minutes (model_manager.py)
  // and a cold reload + generation on this project's real target hardware
  // can take up to ~90s on its own (Phase 8's Locust findings) — generous
  // headroom here reflects real, disclosed latency, not a hang.
  timeout: 330_000, // must cover the exam-prep MCQ test's own 240s + 60s waits, plus headroom
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  globalSetup: "./e2e/global-setup.ts",
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Most tests reuse one logged-in session (see global-setup.ts) rather
    // than each calling the rate-limited /auth/login themselves.
    // auth.spec.ts overrides this per-test where it needs a logged-out or
    // freshly-registered state instead.
    storageState: "e2e/.auth/demo.json",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
