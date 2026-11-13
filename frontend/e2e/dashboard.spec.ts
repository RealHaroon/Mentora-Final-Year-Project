import { test, expect } from "@playwright/test";

// Phase 2 §8 item 5, plus the 2026-11-10 at-risk-check wiring: every section
// renders from a real backend fetch, not the original Phase 2 hardcoded JSX.
// Runs against the shared logged-in demo session (see global-setup.ts).

test("a real action produces a real, specific notification — not one of 4 fixed messages", async ({ page }) => {
  // Found 2026-11-13: GET /notifications returned the exact same 4
  // hardcoded items for every account regardless of what they'd actually
  // done, even though /dashboard/at-risk-check already wrote real rows to
  // the Notification table — this endpoint just never read them. Playlist
  // adds are the easiest real trigger to drive from the UI directly.
  const title = `Notification test video ${Date.now()}`;
  await page.goto("/learning-portal");
  await page.getByRole("button", { name: "Add Video" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Subject").selectOption("Physics");
  await page.getByLabel("Source").fill("Playwright");
  await page.getByLabel("Duration (min)").fill("5");
  await page.getByRole("button", { name: "Add to playlist" }).click();
  await expect(page.locator(".media-row").filter({ hasText: title })).toBeVisible({ timeout: 10_000 });

  await page.goto("/dashboard");
  await expect(page.getByText("🔔 Notifications")).toBeVisible();
  await expect(page.locator(".notif-item.ok", { hasText: title })).toBeVisible({ timeout: 10_000 });
});

test("dashboard renders real data for every section, including the AI risk check", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page.getByText("Ayesha Memon")).toBeVisible();
  await expect(page.getByText(/Score trend \(last \d+ sessions\)/)).toBeVisible();
  await expect(page.getByText("This week's timetable snapshot")).toBeVisible();

  // M3 (Trajectory Predictor) — the demo account has >=5 scored sessions, so
  // this should resolve to a real prediction, not the "need N more" message.
  await expect(page.getByText(/AI Risk Check/)).toBeVisible();
  await expect(page.getByText(/Predicted next score: \d+% · Trend: (stable|declining|improving)/)).toBeVisible();

  // Weak Topics: either real flagged rows or the explicit empty state — never
  // a silently blank section (the gap the 2026-11-10 audit fixed).
  const weakTopicsEmpty = page.getByText("No weak topics flagged yet");
  const weakTopicsHeading = page.getByText("⚠ Weak Topics (AI flagged)");
  await expect(weakTopicsHeading).toBeVisible();
  const hasEmptyState = await weakTopicsEmpty.isVisible().catch(() => false);
  if (!hasEmptyState) {
    await expect(page.locator(".weak-item").first()).toBeVisible();
  }

  await expect(page.getByText("🔔 Notifications")).toBeVisible();
});

test("logged-out user cannot reach the dashboard after logging out", async ({ page }) => {
  await page.goto("/dashboard");
  // handleLogout (SiteHeader.tsx) awaits the logout fetch, then
  // router.push("/") — wait for that navigation to actually land before
  // checking /dashboard again, otherwise this races ahead of the
  // session cookie actually being cleared in the browser.
  await Promise.all([page.waitForURL("/"), page.getByRole("button", { name: "Logout" }).click()]);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});
