import { test, expect } from "@playwright/test";

// Dashboard settings panel (components/DashboardSettings.tsx). Deliberately
// does NOT automate the change-password flow: this was tested live by hand
// on 2026-11-10 and worked, but a test that mutates the demo account's own
// login credentials is a real liability if interrupted mid-run (a browser
// disconnect during that exact manual test left the account on a temporary
// password until it was reverted via a direct API call) — not a risk worth
// taking for a flow that doesn't touch frontend/backend wiring correctness
// any differently than the profile-edit test below already covers.

test("notification preferences load real values and persist after save+reload", async ({ page }) => {
  await page.goto("/dashboard#settings");
  await page.getByRole("button", { name: "Notification Prefs" }).click();

  const weakTopicAlerts = page.getByLabel(/Weak-topic alerts/);
  await expect(weakTopicAlerts).toBeVisible({ timeout: 10_000 });
  const wasChecked = await weakTopicAlerts.isChecked();

  await weakTopicAlerts.setChecked(!wasChecked);
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page.getByText("Notification preferences saved")).toBeVisible();

  await page.reload();
  await page.getByRole("button", { name: "Notification Prefs" }).click();
  await expect(page.getByLabel(/Weak-topic alerts/)).toBeChecked({ checked: !wasChecked, timeout: 10_000 });

  // Restore the original value — this test should be idempotent across runs.
  await page.getByLabel(/Weak-topic alerts/).setChecked(wasChecked);
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page.getByText("Notification preferences saved")).toBeVisible();
});

test("changing exam goal to MDCAT actually changes which subjects Exam Prep offers", async ({ page }) => {
  // Found 2026-11-14: exam_goal was captured at registration and then never
  // read anywhere — every goal saw the identical subject list regardless,
  // and there was no UI to even change it after signing up. Restores the
  // original goal at the end — this is the shared demo account, and other
  // tests/manual testing assume it's "sindh_university".
  await page.goto("/dashboard#settings");
  await page.getByRole("button", { name: "👤 Account" }).click();

  const goalField = page.getByLabel("I am preparing for");
  await expect(goalField).toBeVisible({ timeout: 10_000 });
  const originalGoal = await goalField.inputValue();

  await goalField.selectOption("mdcat");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Profile updated")).toBeVisible({ timeout: 10_000 });

  await page.goto("/exam-prep");
  const subjectSelector = page.locator("#subject-selector");
  await expect(subjectSelector.getByText("Biology", { exact: false })).toBeVisible({ timeout: 10_000 });
  // MDCAT doesn't test Mathematics — it must not appear as an offered chip.
  await expect(subjectSelector.getByText("Mathematics", { exact: false })).toHaveCount(0);

  await page.goto("/dashboard#settings");
  await page.getByRole("button", { name: "👤 Account" }).click();
  await page.getByLabel("I am preparing for").selectOption(originalGoal);
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Profile updated")).toBeVisible({ timeout: 10_000 });
});

test("profile edit saves and the server-rendered header refreshes with the new value", async ({ page }) => {
  await page.goto("/dashboard#settings");
  await page.getByRole("button", { name: "👤 Account" }).click();

  const universityField = page.getByLabel("University / Institution");
  await expect(universityField).toBeVisible({ timeout: 10_000 });
  // A fixed, idempotent value — safe to set on every run regardless of what
  // the field currently holds.
  await universityField.fill("University of Sindh, Laar Campus (Playwright-verified)");
  await page.getByRole("button", { name: "Save changes" }).click();

  // The header is a Server Component — only a real router.refresh() after a
  // real PATCH would make it show the new value without a manual reload.
  await expect(page.getByText("University of Sindh, Laar Campus (Playwright-verified)")).toBeVisible({ timeout: 10_000 });
});
