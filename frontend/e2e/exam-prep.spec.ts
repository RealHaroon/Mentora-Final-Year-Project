import { test, expect } from "@playwright/test";

// Phase 2 §8 item 7, plus the 2026-11-10 fixes: the Promise.all gating bug
// (fast sections stuck behind the slow MCQ call) and the MCQ null-correctness
// handling. Runs against the shared logged-in demo session (see
// global-setup.ts).
//
// Order matters here: every /exam-prep visit fires a real /exam/mcq call in
// the background regardless of what the test itself waits on (that's the
// bug this file's first test guards against — it must NOT be blocking).
// M2 serializes generation behind one shared lock (heavy_lock), so an
// earlier test's now-orphaned background call would otherwise queue in
// front of this file's one MCQ-dependent test and roughly double its wait.
// Keeping that test first avoids the contention entirely.

test("MCQ loads and submitting an answer shows a real graded or ungraded result", async ({ page }) => {
  await page.goto("/exam-prep");

  const mcqForm = page.locator("#mcq-form");
  // M2 idle-unloads after 5 minutes and a cold reload + generation can take
  // up to ~90s on its own (Phase 8's Locust findings) — and considerably
  // longer under the same real-RAM contention Phase 8 §12's pitfall table
  // already documents (other browser tabs/processes competing for this
  // machine's genuinely tight 8GB budget can push the whole system into
  // swap, which is what a slow CI/dev box running this suite alongside
  // anything else looks like). Generous on purpose — this is real,
  // disclosed latency, not a hang.
  await expect(mcqForm.getByRole("radio").first()).toBeVisible({ timeout: 240_000 });

  // React 18/19 Strict Mode double-invokes effects in dev, so loadAll()'s
  // /exam/mcq fetch actually fires twice on mount — the second response can
  // silently replace the whole question/radio group right as this test is
  // mid-interaction (checked a radio from the FIRST question, then clicking
  // Submit on a form that's quietly become the SECOND question with nothing
  // checked — handleMcqSubmit's `if (!answer) return` then makes Submit a
  // silent no-op). Letting the network settle first avoids racing that.
  await page.waitForLoadState("networkidle", { timeout: 5_000 }).catch(() => {});

  await mcqForm.getByRole("radio").first().check();
  await mcqForm.getByRole("button", { name: "Submit →" }).click();

  // Exactly one of these three real outcomes must appear — the bug this
  // guards against rendered "the correct answer is null" for the common
  // (no labeled answer) case instead of any of these.
  const correct = page.getByText("Correct!");
  const incorrect = page.getByText(/Not quite — the correct answer is/);
  const ungraded = page.getByText(/no labeled correct answer|isn't gradable/);
  // On a wrong answer this calls M1 (gap_classifier) — normally fast, but
  // under the same real memory contention as M2 above, a "fast" model can
  // still queue/slow down noticeably. Generous for the same reason.
  await expect(correct.or(incorrect).or(ungraded)).toBeVisible({ timeout: 60_000 });

  // Found 2026-11-12: there was no way to progress past the first question
  // at all — submitting just left the same question on screen forever, with
  // no "next" affordance, despite the panel's own "X remaining" counter
  // implying a multi-question session. Fixed by adding real client-side
  // session progression; this guards against that regression.
  await expect(page.getByText("Question 1 of 5")).toBeVisible();
  await mcqForm.getByRole("button", { name: "Next Question →" }).click();
  await expect(mcqForm.getByRole("radio").first()).toBeVisible({ timeout: 240_000 });
  await expect(page.getByText("Question 2 of 5")).toBeVisible();
  // The previous question's graded result must not still be showing against
  // the new question.
  await expect(correct.or(incorrect).or(ungraded)).not.toBeVisible();
  await expect(mcqForm.getByRole("button", { name: "Submit →" })).toBeVisible();
});

test("timetable and today's topic render without waiting for the slow MCQ call", async ({ page }) => {
  await page.goto("/exam-prep");

  // These two are fast mock endpoints — if the old Promise.all gating bug
  // were still present, they'd stay on "Loading…" for as long as /exam/mcq
  // takes (60-90s for a cold M2 generation). A short timeout here is the
  // actual regression test: it must NOT need to wait anywhere near that long.
  await expect(page.locator(".stat-block .stat-num")).toBeVisible({ timeout: 10_000 }); // days-to-exam stat
  await expect(page.getByRole("heading", { name: /Today's Topic/ })).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("AI-Generated Study Timetable")).toBeVisible();
  await expect(page.locator("table.data-table tbody tr").first()).toBeVisible({ timeout: 10_000 });
});

test("curating a real video in Settings makes Exam Prep's Watch button use it", async ({ page }) => {
  // Found 2026-11-15: the suggested video had no real link at all until
  // Add to Playlist, and even then it was a generic (if correctly-queried,
  // post-2026-11-14-fix) YouTube search, never a specific real video. This
  // checks the full real path: curate a video for whatever topic Exam Prep
  // is actually showing today, confirm the Watch button picks it up, then
  // revert so the shared demo account isn't left with test data.
  await page.goto("/exam-prep");
  // Must wait for the populated heading specifically ("Today's Topic: X")
  // — the bare "Today's Topic" loading-state text is present immediately
  // and reading it too early gets "X" as an empty string.
  const headingLocator = page.getByRole("heading", { name: /Today's Topic:/ });
  await expect(headingLocator).toBeVisible({ timeout: 10_000 });
  const heading = await headingLocator.innerText();
  const topic = heading.replace(/^Today's Topic:\s*/, "").trim();

  // Manage Topic Videos moved to its own /admin page 2026-11-15 — was
  // previously a toggled panel inside Dashboard Settings.
  await page.goto("/admin");
  // Exact text match, not .filter({ hasText: topic }) — found 2026-11-16:
  // that's a case-insensitive SUBSTRING match, and "Organic Chemistry" is
  // literally a substring of "Inorganic Chemistry" (also a real topic in
  // this list, sorting first alphabetically) — .first() silently filled in
  // the wrong row whenever today's real topic was "Organic Chemistry". The
  // revert step below already used exact matching correctly; this just
  // never got the same fix.
  const row = page.locator(".field-row", { has: page.getByText(topic, { exact: true }) }).first();
  await expect(row.getByPlaceholder("https://www.youtube.com/watch?v=...")).toBeVisible({ timeout: 10_000 });
  await row.getByPlaceholder("Video title").fill(`${topic} — Playwright Test Video`);
  await row.getByPlaceholder("https://www.youtube.com/watch?v=...").fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
  const [putResponse] = await Promise.all([
    page.waitForResponse((res) => res.url().includes("/exam/topic-videos/") && res.request().method() === "PUT"),
    row.getByRole("button", { name: "Save" }).click(),
  ]);
  expect(putResponse.status(), await putResponse.text()).toBe(200);
  await expect(page.getByText(`Video saved for ${topic}`)).toBeVisible({ timeout: 10_000 });

  await page.goto("/exam-prep");
  await expect(page.getByRole("heading", { name: /Today's Topic/ })).toBeVisible({ timeout: 10_000 });
  const watchLink = page.getByRole("link", { name: "▶ Watch" });
  await expect(watchLink).toHaveAttribute("href", "https://www.youtube.com/watch?v=dQw4w9WgXcQ");
  await expect(page.getByText("Curated")).toBeVisible();

  // Revert — don't leave the shared demo account's topic permanently
  // pointed at a test video.
  await page.goto("/admin");
  const row2 = page.locator(".field-row", { has: page.getByText(topic, { exact: true }) }).first();
  await row2.getByRole("button", { name: "Remove" }).click();
  await expect(page.getByText(`Reverted ${topic} to the default search link`)).toBeVisible({ timeout: 10_000 });
});

test("ask-AI topic explainer returns a real RAG answer", async ({ page }) => {
  await page.goto("/exam-prep");
  // Found 2026-11-15 testing live: this box's own position shifts as the
  // page's other async sections (today-topic, MCQ) finish loading and grow
  // — interacting with it before the page settles can click/type into the
  // wrong element entirely (the panel above it had already grown past the
  // reserved minHeight once, in one case landing a click on an MCQ radio
  // instead). Waiting for the real explainer text — not just "Loading…" —
  // before interacting avoids that same race here.
  await expect(page.locator("#topic-explainer")).not.toContainText("Loading…", { timeout: 15_000 });

  await page.getByPlaceholder(/How do I factor a quadratic/).fill("What is the quadratic formula?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByRole("button", { name: "Asking…" })).toBeVisible();
  // Groq-backed RAG call — a few seconds normally, generous timeout for a
  // cold connection (Phase 9 §9's pre-warm rationale).
  await expect(page.getByRole("button", { name: "Ask" })).toBeVisible({ timeout: 30_000 });

  // The previous version of this test only checked the button's own
  // loading-state cycle, which would have passed even if the answer never
  // actually rendered — assert real, specific content instead. A dedicated
  // data-testid, not DOM-order matching: the explainer's own summary <p>
  // sits earlier in the same panel and isn't a reliable "last paragraph".
  const answer = page.getByTestId("topic-ask-answer");
  await expect(answer).toBeVisible();
  await expect(answer).not.toBeEmpty();
  const text = (await answer.innerText()).toLowerCase();
  expect(text).toMatch(/quadratic|formula|discriminant/);
});
