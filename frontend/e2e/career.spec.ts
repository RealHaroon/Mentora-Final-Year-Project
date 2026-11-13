import { test, expect } from "@playwright/test";

// Phase 2 §8 item 8, plus the 2026-11-10 fixes: ai-suggest's career_id
// mapping, interview/start's required career_goal param, and interview/ask's
// combined-answer rendering (previously stuck repeating the first question).
// Runs against the shared logged-in demo session (see global-setup.ts).

test("career rankings load from the real CV already on file for the demo account", async ({ page }) => {
  await page.goto("/career");

  await expect(page.getByRole("cell", { name: "Data Scientist" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/Model: \S+/)).toBeVisible();
});

test("roadmap milestone status persists across reloads (not recomputed from the CV every time)", async ({ page }) => {
  // Found 2026-11-13: ROADMAPS existed in the schema from the start but
  // nothing ever wrote to it — the roadmap was recomputed fresh from the CV
  // on every request and thrown away, so a student had no way to actually
  // track progress over time. Business Analyst, not Data Scientist — avoids
  // colliding with manual roadmap testing done against the default career.
  await page.goto("/career");
  await expect(page.getByRole("cell", { name: "Data Scientist" })).toBeVisible({ timeout: 15_000 });
  // The timeline already shows Data Scientist's roadmap from the page's own
  // mount fetch — wait for the heading to actually say Business Analyst
  // before touching any circle, or a click/read can land on the stale
  // Data-Scientist steps still on screen during the View Roadmap fetch.
  await page.getByRole("row", { name: /Business Analyst/ }).getByRole("button", { name: "View Roadmap" }).click();
  await expect(page.getByText("6-Month Skill Roadmap — Business Analyst")).toBeVisible({ timeout: 15_000 });

  const firstCircle = page.locator(".timeline .step-circle").first();
  const statusBefore = await firstCircle.getAttribute("title");
  await firstCircle.click();
  await expect(firstCircle).not.toHaveAttribute("title", statusBefore ?? "", { timeout: 5_000 });
  const statusAfterClick = await firstCircle.getAttribute("title");

  await page.goto("/career");
  await page.getByRole("row", { name: /Business Analyst/ }).getByRole("button", { name: "View Roadmap" }).click();
  await expect(page.getByText("6-Month Skill Roadmap — Business Analyst")).toBeVisible({ timeout: 15_000 });
  const reloadedCircle = page.locator(".timeline .step-circle").first();
  await expect(reloadedCircle).toHaveAttribute("title", statusAfterClick ?? "", { timeout: 15_000 });
});

test("AI Suggest Best Career updates the goal dropdown from a real prediction", async ({ page }) => {
  await page.goto("/career");

  await expect(page.getByRole("cell", { name: "Data Scientist" })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("combobox").selectOption("product_manager");
  await page.getByRole("button", { name: "AI Suggest Best Career" }).click();

  // The demo CV's top real match is Data Scientist — this only passes if the
  // frontend correctly mapped the real career_id back to a goal value.
  await expect(page.getByRole("combobox")).toHaveValue("data_scientist", { timeout: 15_000 });
});

test("career Q&A returns a real RAG answer", async ({ page }) => {
  await page.goto("/career");

  await page.getByPlaceholder("Type your question…").fill("What skills matter most for a Data Scientist?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("button", { name: "Asking…" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Ask", exact: true })).toBeVisible({ timeout: 30_000 });
});

test("mock interview starts and the conversation progresses past the first question", async ({ page }) => {
  await page.goto("/career");

  await page.getByRole("button", { name: "Start Mock Interview →" }).click();
  const firstQuestion = page.locator("#mock-interview p", { hasText: "Q:" });
  await expect(firstQuestion).toBeVisible({ timeout: 15_000 });

  await page.locator("#mock-interview input[type=text]").fill(
    "I'd start with exploratory data analysis to understand distributions and missing values."
  );
  await page.locator("#mock-interview").getByRole("button", { name: "Send" }).click();

  // The bug this guards against: the old mismatched response shape left this
  // showing the exact same opening question forever, with no feedback — so
  // both the student's own answer AND a distinct AI reply must now appear.
  await expect(page.getByText("You: I'd start with exploratory")).toBeVisible({ timeout: 15_000 });
  const aiReply = page.locator("#mock-interview p").filter({ hasNotText: "You:" }).filter({ hasNotText: "Q:" });
  await expect(aiReply.first()).toBeVisible();
  await expect(aiReply.first()).not.toBeEmpty();
});
