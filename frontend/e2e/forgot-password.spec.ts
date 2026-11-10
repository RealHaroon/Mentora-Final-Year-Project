import { readFileSync } from "node:fs";
import { test, expect } from "@playwright/test";
import { uniqueTestEmail } from "./helpers";

// Phase 2 §8 item 10. No RAG/ML involvement, so no shape-drift expected
// (unlike exam/career) — confirmed 2026-11-11 via a live manual run, this
// just locks that in as a regression test.
//
// The reset code isn't emailed (no email service wired up — by design,
// disclosed on the page itself); it's printed to the backend's own stdout.
// The full-flow test below reads that code straight from the backend's log
// file (BACKEND_LOG_PATH), the same way a developer verifying this locally
// would read the terminal. Without that env var set, only the two
// code-independent tests below run.

function readLatestResetCode(email: string): string | null {
  const logPath = process.env.BACKEND_LOG_PATH;
  if (!logPath) return null;
  const log = readFileSync(logPath, "utf8");
  const matches = [...log.matchAll(new RegExp(`password reset code for ${email}: (\\d{6})`, "g"))];
  return matches.length > 0 ? matches[matches.length - 1][1] : null;
}

test.use({ storageState: { cookies: [], origins: [] } });

test("forgot-password request always returns the same generic success message", async ({ page }) => {
  // This half needs no reset code — safe to run unconditionally, and it's
  // the one Phase 8 §8 security property worth locking in: the response
  // must not reveal whether the email is actually registered.
  await page.goto("/forgot-password");
  await page.getByLabel("Registered Email Address").fill("definitely-not-registered@example.com");
  await page.getByRole("button", { name: "Send Reset Link →" }).click();
  await expect(page.getByText("If that email is registered, a reset code has been sent.")).toBeVisible({
    timeout: 10_000,
  });
});

test("reset-password form rejects a wrong code with a generic error, not a crash", async ({ page }) => {
  await page.goto("/forgot-password");
  await page.getByLabel("Reset Code (from email)").fill("000000");
  await page.getByLabel("New Password", { exact: true }).fill("somenewpassword123");
  await page.getByLabel("Confirm New Password").fill("somenewpassword123");
  await page.getByRole("button", { name: "Reset Password →" }).click();
  await expect(page.getByText("Invalid or expired reset code")).toBeVisible({ timeout: 10_000 });
});

test("full reset flow: request a code, use it to set a new password, then log in with it", async ({ page }) => {
  test.skip(!process.env.BACKEND_LOG_PATH, "requires BACKEND_LOG_PATH pointing at the running backend's log file");
  const email = uniqueTestEmail();

  await page.goto("/register");
  await page.getByLabel("First Name").fill("Reset");
  await page.getByLabel("Last Name").fill("FlowTest");
  await page.getByLabel("Email Address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("originalpass123");
  await page.getByLabel("Confirm Password").fill("originalpass123");
  await page.getByLabel("University / Institution").fill("Test University");
  await page.getByLabel("I am preparing for").selectOption("sindh_university");
  await page.getByRole("button", { name: "Create Account →" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await page.getByRole("button", { name: "Logout" }).click();

  await page.goto("/forgot-password");
  await page.getByLabel("Registered Email Address").fill(email);
  await page.getByRole("button", { name: "Send Reset Link →" }).click();
  await expect(page.getByText("If that email is registered")).toBeVisible();

  // Give the backend a moment to flush its print before reading the log.
  await page.waitForTimeout(500);
  const code = readLatestResetCode(email);
  expect(code, `no reset code found in ${process.env.BACKEND_LOG_PATH} for ${email}`).not.toBeNull();

  await page.getByLabel("Reset Code (from email)").fill(code!);
  await page.getByLabel("New Password", { exact: true }).fill("brandnewpassword456");
  await page.getByLabel("Confirm New Password").fill("brandnewpassword456");
  await page.getByRole("button", { name: "Reset Password →" }).click();
  await expect(page.getByText("Password reset — you can log in with your new password now.")).toBeVisible({
    timeout: 10_000,
  });

  await page.goto("/login");
  await page.getByLabel("Email Address").fill(email);
  await page.getByLabel("Password").fill("brandnewpassword456");
  await page.getByRole("button", { name: "Login →" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
});
