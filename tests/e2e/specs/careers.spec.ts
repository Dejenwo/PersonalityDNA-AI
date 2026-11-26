import { expect, test } from "@playwright/test";
import { answer, expectAccessible } from "./helpers";

test("career interests: take the assessment, see the code and the career exploration page", async ({ page }) => {
  // Before any results, the careers page invites the visitor to take the assessments.
  await page.goto("/careers");
  await expect(page.getByRole("heading", { name: "Career exploration" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Take the interest assessment" })).toBeVisible();
  await expectAccessible(page);

  await page.goto("/discover");
  await expect(page.getByText("Preview")).toBeVisible();
  await page.getByRole("link", { name: /Start Career Interests/ }).click();
  await expect(page.getByText(/not affiliated with or endorsed by USDOL\/ETA/)).toBeVisible();
  await expectAccessible(page);
  await page.getByLabel("I confirm I am 18 or older.").check();
  await page.getByLabel(/I agree that PersonalityDNA stores/).check();
  await page.getByRole("button", { name: "Begin assessment" }).click();

  // Items 11 to 40 are Investigative, Artistic and Social: like those, skip the rest.
  for (let i = 1; i <= 60; i++) await answer(page, i, 60, i > 10 && i <= 40 ? "I'd like to do this" : "Not for me");
  await page.getByRole("button", { name: "See my results" }).click();

  await expect(page.getByRole("heading", { name: "Interest code IAS" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Investigative: 10 of 10 activities chosen" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Realistic: 0 of 10 activities chosen" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Preview" })).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("link", { name: "Career exploration", exact: true }).click();
  await expect(page).toHaveURL(/\/careers$/);
  await expect(page.getByRole("heading", { name: "Your career interests: code IAS" })).toBeVisible();
  await expect(page.getByRole("link", { name: "See your full interest results" })).toBeVisible();
  await expect(page.getByText("Take a Big Five personality assessment")).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in to explore with the coach" })).toHaveAttribute(
    "href",
    "/login?next=%2Fcoach%3Ftopic%3Dcareer",
  );
  await expectAccessible(page);
});
