import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([]);
}

async function startQuick(page: Page) {
  await page.goto("/discover");
  await page.getByRole("link", { name: /Start Quick Discovery/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Quick Discovery");
  await page.getByLabel("I confirm I am 18 or older.").check();
  await page.getByLabel(/I agree that PersonalityDNA stores/).check();
  await page.getByRole("button", { name: "Begin assessment" }).click();
  await expect(page).toHaveURL(/\/assessment\/[0-9a-f-]+$/); // token removed from the address bar
}

async function answerCurrent(page: Page, label: string) {
  await page.getByRole("radio", { name: label }).check();
}

/** Answer statement `n` (1-based) of `total` and wait for the auto-advance. */
async function answer(page: Page, n: number, total: number, label: string) {
  await expect(page.getByText(`Statement ${n} of ${total}`)).toBeVisible();
  await answerCurrent(page, label);
  if (n < total) await expect(page.getByText(`Statement ${n + 1} of ${total}`)).toBeVisible();
}

test("home and discover pages are accessible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expectAccessible(page);
  await page.goto("/discover");
  await expect(page.getByRole("link", { name: /Start Quick Discovery/ })).toBeVisible();
  await expectAccessible(page);
});

test("consent is required before starting", async ({ page }) => {
  await page.goto("/discover/mini-ipip-20");
  const begin = page.getByRole("button", { name: "Begin assessment" });
  await expect(begin).toBeDisabled();
  await page.getByLabel("I confirm I am 18 or older.").check();
  await expect(begin).toBeDisabled();
  await expectAccessible(page);
});

test("full journey: start, autosave, resume after reload, finish, view results", async ({ page }) => {
  await startQuick(page);
  await expect(page.getByText("Statement 1 of 20")).toBeVisible();
  await expectAccessible(page);

  const labels = ["Moderately accurate", "Very accurate", "Neither accurate nor inaccurate", "Moderately inaccurate"];
  for (let i = 0; i < 8; i++) {
    await answerCurrent(page, labels[i % labels.length]!);
    await expect(page.getByText(`Statement ${i + 2} of 20`)).toBeVisible();
  }
  await expect(page.getByText("All answers saved")).toBeVisible();

  // Reload: progress is restored from the server and we land on the first unanswered statement.
  await page.reload();
  await expect(page.getByText("8 of 20 answered")).toBeVisible();
  await expect(page.getByText("Statement 9 of 20")).toBeVisible();

  // Going back shows the saved answer.
  await page.getByRole("button", { name: "Back" }).click();
  await expect(page.getByRole("radio", { name: labels[7 % labels.length]! })).toBeChecked();
  await page.getByRole("button", { name: "Next" }).click();

  for (let i = 8; i < 20; i++) await answer(page, i + 1, 20, labels[i % labels.length]!);
  await expect(page.getByRole("heading", { name: /All done/ })).toBeVisible();
  await page.getByRole("button", { name: "See my results" }).click();

  await expect(page).toHaveURL(/\/results\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: "Your Big Five traits" })).toBeVisible();
  for (const t of ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Emotional Stability"]) {
    await expect(page.getByRole("heading", { name: t, level: 3 }).first()).toBeVisible();
  }
  await expect(page.getByText("Primary archetype")).toBeVisible();
  await expect(page.getByText(/not a percentile/)).toBeVisible();
  // Finished in seconds, so the quality note must appear.
  await expect(page.getByText(/completed very quickly/)).toBeVisible();
  await expectAccessible(page);

  // History lists the completed assessment and reopens the results.
  await page.goto("/history");
  await page.getByRole("link", { name: "View results" }).first().click();
  await expect(page.getByRole("heading", { name: "Your Big Five traits" })).toBeVisible();
});

test("skipped statements are listed before finishing", async ({ page }) => {
  await startQuick(page);
  await page.getByRole("button", { name: "Skip" }).click();
  for (let i = 1; i < 20; i++) await answer(page, i + 1, 20, "Moderately accurate");
  await expect(page.getByRole("heading", { name: "Almost there" })).toBeVisible();
  await page.getByRole("button", { name: "See my results" }).click();
  await expect(page.getByText("Please answer more questions before finishing.")).toBeVisible();
  await page.getByRole("button", { name: "Statement 1", exact: true }).click();
  await answerCurrent(page, "Very inaccurate");
  await expect(page.getByRole("heading", { name: /All done/ })).toBeVisible();
  await page.getByRole("button", { name: "See my results" }).click();
  await expect(page.getByRole("heading", { name: "Your Big Five traits" })).toBeVisible();
});

test("results are private to the device that took the assessment", async ({ browser, page }) => {
  await startQuick(page);
  const url = page.url();
  const other = await browser.newContext();
  const stranger = await other.newPage();
  await stranger.goto(url);
  await expect(stranger.getByRole("heading", { name: /can't find this assessment on this device/ })).toBeVisible();
  await other.close();
});
