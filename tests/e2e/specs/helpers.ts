import AxeBuilder from "@axe-core/playwright";
import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const API = "http://127.0.0.1:8000";
export const PASSWORD = "a long and memorable passphrase";

export async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([]);
}

export function uniqueEmail(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

/** Reads the newest emailed link of a kind from the development outbox. */
export async function emailLink(request: APIRequestContext, to: string, kind: string): Promise<string> {
  let link: string | undefined;
  await expect
    .poll(async () => {
      const res = await request.get(`${API}/api/v1/dev/outbox`, { params: { to } });
      const items = (await res.json()).items as { kind: string; text: string }[];
      link = items.filter((i) => i.kind === kind).at(-1)?.text.match(/https?:\/\/\S+#token=[\w-]+/)?.[0];
      return link;
    })
    .toBeTruthy();
  return link!;
}

export async function answer(page: Page, n: number, total: number, label: string) {
  await expect(page.getByText(`Statement ${n} of ${total}`)).toBeVisible();
  await page.getByRole("radio", { name: label }).check();
  if (n < total) await expect(page.getByText(`Statement ${n + 1} of ${total}`)).toBeVisible();
}

export async function takeQuickAssessment(page: Page) {
  await page.goto("/discover/mini-ipip-20");
  await page.getByLabel("I confirm I am 18 or older.").check();
  await page.getByLabel(/I agree that PersonalityDNA stores/).check();
  await page.getByRole("button", { name: "Begin assessment" }).click();
  const labels = ["Moderately accurate", "Very accurate", "Moderately inaccurate"];
  for (let i = 0; i < 20; i++) await answer(page, i + 1, 20, labels[i % 3]!);
  await page.getByRole("button", { name: "See my results" }).click();
  await expect(page.getByRole("heading", { name: "Your Big Five traits" })).toBeVisible();
}

export async function registerAndVerify(page: Page, request: APIRequestContext, email: string) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByLabel("I confirm I am 18 or older.").check();
  await page.getByLabel(/I agree to the/).check();
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
  await page.goto(await emailLink(request, email, "verify_email"));
  await expect(page.getByRole("heading", { name: "Email confirmed" })).toBeVisible();
}

export async function signIn(page: Page, email: string, password = PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "My results" })).toBeVisible();
}
