import { test, expect } from "@playwright/test";

// /learning-portal's playlist/materials/watch-history were plain module-level
// Python lists until 2026-11-12 — not just "not persisted to a DB" but shared
// across EVERY user of the process, and de-duplicated only by title. A fixed
// test title would silently collide with a previous run's leftover entry and
// surface as a confusing duplicate in the UI (which is exactly what happened
// — see the 2026-11-10 fix to PlaylistSection.tsx's handleAddVideo for the
// frontend half of that). Fixed backend-side 2026-11-12: playlist, watch
// history, and self-uploaded materials now live in real per-user DB tables
// (database/models.py's PlaylistItem/WatchHistoryEntry/Material); only the
// catalogue materials (board past papers etc.) are intentionally shared.
// Still using a title unique to this run below — real per-user isolation
// removes the cross-USER collision risk, not collisions between this test's
// own runs against the same demo account.

function uniqueTitle() {
  return `Playwright test video ${Date.now()}`;
}

test("learning portal loads real stats, playlist, assignments, and materials", async ({ page }) => {
  await page.goto("/learning-portal");

  await expect(page.getByText("Videos in Playlist")).toBeVisible();
  await expect(page.locator(".media-row").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "MCQ Assignments" })).toBeVisible();
  await expect(page.getByText("Course PDFs").first()).toBeVisible();
  await expect(page.getByText("MDCAT Biology Full Syllabus 2025")).toBeVisible();
});

test("add a video to the playlist, watch it (logs to watch history), then remove it", async ({ page }) => {
  const title = uniqueTitle();
  await page.goto("/learning-portal");

  await page.getByRole("button", { name: "Add Video" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Subject").selectOption("Mathematics");
  await page.getByLabel("Source").fill("Playwright");
  await page.getByLabel("Duration (min)").fill("5");
  await page.getByRole("button", { name: "Add to playlist" }).click();

  // Scoped to rows with a Remove button — watch-history rows (same
  // ".media-row" class, same title once logged) have no action buttons at
  // all, so a plain hasText match would ambiguously match both.
  const playlistRow = page
    .locator(".media-row")
    .filter({ hasText: title })
    .filter({ has: page.getByRole("button", { name: "Remove" }) });
  await expect(playlistRow).toBeVisible({ timeout: 10_000 });

  // "Watch" opens a new tab (window.open) and logs a real watch-history entry
  // — don't wait on the popup, just confirm the history side-effect landed.
  const popupPromise = page.waitForEvent("popup").catch(() => null);
  await playlistRow.getByRole("button", { name: "Watch" }).click();
  await popupPromise;

  await page.locator('a[href="#watch-history"]').first().click();
  const historyRow = page.locator("h3#watch-history ~ .media-row").filter({ hasText: title });
  await expect(historyRow.first()).toBeVisible({ timeout: 10_000 });

  await playlistRow.getByRole("button", { name: "Remove" }).click();
  await expect(playlistRow).not.toBeVisible({ timeout: 10_000 });
});

test("subject filter narrows the playlist to a real server-side query, not a client-side no-op", async ({ page }) => {
  const title = uniqueTitle();
  await page.goto("/learning-portal");

  await page.getByRole("button", { name: "Add Video" }).click();
  await page.getByLabel("Title").fill(title);
  await page.getByLabel("Subject").selectOption("Chemistry");
  await page.getByLabel("Source").fill("Playwright");
  await page.getByLabel("Duration (min)").fill("5");
  await page.getByRole("button", { name: "Add to playlist" }).click();
  await expect(page.locator(".media-row").filter({ hasText: title })).toBeVisible({ timeout: 10_000 });

  await page.getByRole("link", { name: "Chemistry", exact: true }).click();
  await expect(page).toHaveURL(/subject=Chemistry/);
  await page.waitForLoadState("networkidle");
  // Scoped to rows with Watch+Remove buttons — the subject filter only
  // applies to the playlist fetch, not the (unrelated) watch-history list,
  // which renders the same ".media-row" class and would otherwise leak
  // unfiltered, buttonless rows into this count.
  const playlistRows = page
    .locator(".media-row")
    .filter({ has: page.getByRole("button", { name: "Remove" }) });
  const ourRow = playlistRows.filter({ hasText: title });
  await expect(ourRow).toBeVisible();
  const count = await playlistRows.count();
  for (let i = 0; i < count; i++) {
    await expect(playlistRows.nth(i).locator(".tag-subject")).toHaveText("Chemistry");
  }

  await ourRow.getByRole("button", { name: "Remove" }).click();
  await expect(ourRow).not.toBeVisible({ timeout: 10_000 });
});
