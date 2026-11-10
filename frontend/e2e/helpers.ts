export const DEMO_EMAIL = "demo@mentora.pk";
export const DEMO_PASSWORD = "MentoraDemo2026!";

export function uniqueTestEmail() {
  return `playwright-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.com`;
}
