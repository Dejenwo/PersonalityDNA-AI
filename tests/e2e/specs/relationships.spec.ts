import { expect, test } from "@playwright/test";
import { expectAccessible, PASSWORD, registerAndVerify, signIn, takeQuickAssessment, uniqueEmail } from "./helpers";

test("relationships: invite, sign in to accept, compare, end", async ({ browser, page, request }) => {
  // Ada has a result and invites her partner.
  const ada = uniqueEmail("ada");
  await registerAndVerify(page, request, ada);
  await signIn(page, ada);
  await takeQuickAssessment(page);
  await page.getByRole("link", { name: "Relationships" }).click();
  await expect(page.getByRole("heading", { name: "Relationships", level: 1 })).toBeVisible();
  await expect(page.getByText("No one yet")).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("button", { name: "Create invitation link" }).click();
  await expect(page.getByText("Please confirm what will be shared.")).toBeVisible();
  await page.getByLabel(/I agree to show the person who accepts/).check();
  await page.getByRole("button", { name: "Create invitation link" }).click();
  const link = await page.getByLabel("Your invitation link").inputValue();
  expect(link).toMatch(/\/relationships\/join#token=[\w-]+$/);
  await expect(page.getByText("Partner invitation")).toBeVisible();
  await expectAccessible(page);

  // Bob opens the link signed out, signs in, and comes back to the invitation.
  const bobContext = await browser.newContext();
  const bobPage = await bobContext.newPage();
  const bob = uniqueEmail("bob");
  await registerAndVerify(bobPage, request, bob);
  await bobPage.goto(link);
  await expect(bobPage).toHaveURL(/\/login\?next=/);
  await bobPage.getByLabel("Email").fill(bob);
  await bobPage.getByLabel("Password").fill(PASSWORD);
  await bobPage.getByRole("button", { name: "Sign in" }).click();
  await expect(bobPage.getByRole("heading", { name: "Someone invited you to compare results" })).toBeVisible();
  expect(bobPage.url()).not.toContain("token=");
  await expectAccessible(bobPage);
  await bobPage.getByLabel(/I agree to show your partner/).check();
  await bobPage.getByRole("button", { name: "Accept invitation" }).click();

  // Bob has no result yet.
  await expect(bobPage.getByRole("heading", { name: "You and your partner" })).toBeVisible();
  await expect(bobPage.getByText("Take a Big Five assessment to see the comparison.")).toBeVisible();
  const comparisonUrl = bobPage.url();
  await takeQuickAssessment(bobPage);
  await bobPage.goto(comparisonUrl);
  const traits = bobPage.getByRole("region", { name: "How you each described yourselves" });
  await expect(traits.getByRole("article")).toHaveCount(5);
  await expect(traits.getByText("Talk about it:").first()).toBeVisible();
  await expect(bobPage.getByText(/%/)).toHaveCount(0);
  await expectAccessible(bobPage);

  // Ada sees the same comparison from her side.
  await page.reload();
  await page.getByRole("link", { name: /Your partner\s+Partner/ }).click();
  await expect(page.getByRole("heading", { name: "You and your partner" })).toBeVisible();
  await expect(page.getByRole("region", { name: "How you each described yourselves" }).getByRole("article")).toHaveCount(5);

  // Bob ends it; Ada can no longer see it.
  await bobPage.getByRole("button", { name: "End comparison" }).click();
  await bobPage.getByRole("button", { name: "End now" }).click();
  await expect(bobPage.getByRole("heading", { name: "Relationships", level: 1 })).toBeVisible();
  await expect(bobPage.getByText("No one yet")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Comparison not available" })).toBeVisible();
  await bobContext.close();
});
