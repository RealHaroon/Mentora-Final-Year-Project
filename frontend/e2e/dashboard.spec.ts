import { test, expect } from "@playwright/test";

// Phase 2 §8 item 5, plus the 2026-11-10 at-risk-check wiring: every section
// renders from a real backend fetch, not the original Phase 2 hardcoded JSX.
// Runs against the shared logged-in demo session (see global-setup.ts).

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
