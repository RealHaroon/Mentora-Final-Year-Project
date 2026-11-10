import { chromium, type FullConfig } from "@playwright/test";
import { DEMO_EMAIL, DEMO_PASSWORD } from "./helpers";

// Logs in once and saves the session cookie for every test that doesn't
// specifically need a logged-out or freshly-registered state. Real reason
// this exists, not just a speed optimization: /auth/login is rate-limited
// to 5/minute per IP (Phase 8 §8 security pass) — every test file logging
// in fresh from the same localhost IP blew through that limit within a
// couple of minutes and caused real, confusing 401s partway through the
// suite.
export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL as string;
  const browser = await chromium.launch();
  const page = await browser.newPage({ baseURL });

  await page.goto("/login");
  await page.getByLabel("Email Address").fill(DEMO_EMAIL);
  await page.getByLabel("Password").fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Login →" }).click();
  await page.waitForURL(/\/dashboard/);

  await page.context().storageState({ path: "e2e/.auth/demo.json" });
  await browser.close();
}
