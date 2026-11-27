import { expect, test } from "@playwright/test";
import { answer, expectAccessible, registerAndVerify, signIn, uniqueEmail } from "./helpers";

const AREAS = 9;

test("leadership: questionnaire, results, modules and progress", async ({ page, request }) => {
  await page.goto("/leadership");
  await expect(page.getByRole("heading", { name: "Leadership development" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Take the leadership questionnaire" })).toBeVisible();
  await expectAccessible(page);

  const email = uniqueEmail("lead");
  await registerAndVerify(page, request, email);
  await signIn(page, email);

  await page.goto("/discover");
  await page.getByRole("link", { name: /Start Leadership Preferences/ }).click();
  await expect(page.getByText(/original reflection questionnaire, not a validated test/)).toBeVisible();
  await page.getByLabel("I confirm I am 18 or older.").check();
  await page.getByLabel(/I agree that PersonalityDNA stores/).check();
  await page.getByRole("button", { name: "Begin assessment" }).click();
  // Statements cycle through the nine areas: love the first area (strategic), dislike the last (planning).
  for (let i = 0; i < 27; i++) {
    const area = i % AREAS;
    await answer(page, i + 1, 27, area === 0 ? "Very much" : area === AREAS - 1 ? "Not at all" : "Somewhat");
  }
  await page.getByRole("button", { name: "See my results" }).click();

  await expect(page.getByRole("heading", { name: "You lean towards Strategic thinking" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Strategic thinking: 100 out of 100" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Planning and organising: 0 out of 100" })).toBeVisible();
  await expect(page.getByText("Build on a strength")).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("link", { name: "Open Plans that work" }).click();
  await expect(page.getByRole("heading", { name: "Plans that work", level: 1 })).toBeVisible();
  await page.getByRole("button", { name: 'Mark "Map one goal" as done' }).click();
  await expect(page.getByRole("button", { name: 'Mark "Map one goal" as not done' })).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("link", { name: "← Leadership" }).click();
  await expect(page.getByRole("heading", { name: "Suggested for you" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Plans that work.*1 of 2 activities done/ })).toBeVisible();
  await expectAccessible(page);
});
