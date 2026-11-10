import { test, expect } from "@playwright/test";
import { uniqueTestEmail } from "./helpers";

// Phase 2 §8, items 1-4: the logged-out redirect, register, logout, login.
// Overrides the config's default logged-in storageState — these tests
// specifically need to start logged out.
test.use({ storageState: { cookies: [], origins: [] } });

test("logged-out visit to a protected route redirects to /login", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});

test("register creates a real account, logs in, logs out, and logs back in", async ({ page }) => {
  const email = uniqueTestEmail();

  await page.goto("/register");
  await page.getByLabel("First Name").fill("Playwright");
  await page.getByLabel("Last Name").fill("Tester");
  await page.getByLabel("Email Address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("testpass123");
  await page.getByLabel("Confirm Password").fill("testpass123");
  await page.getByLabel("University / Institution").fill("University of Sindh, Laar Campus");
  await page.getByLabel("I am preparing for").selectOption("sindh_university");
  await page.getByRole("button", { name: "Create Account →" }).click();

  await expect(page).toHaveURL(/\/dashboard/);
  // Real registered name should render from a real /users/me fetch, not a
  // leftover mock — the Phase 2 §8 regression this guards against.
  await expect(page.getByText("Playwright Tester")).toBeVisible();

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login|\/$/);

  await page.goto("/login");
  await page.getByLabel("Email Address").fill(email);
  await page.getByLabel("Password").fill("testpass123");
  await page.getByRole("button", { name: "Login →" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByText("Playwright Tester")).toBeVisible();
});
