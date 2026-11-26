import { expect, test } from "@playwright/test";
import { expectAccessible, PASSWORD, registerAndVerify, takeQuickAssessment, uniqueEmail } from "./helpers";

test("coach: sign in from results, consent, chat, crisis support and delete", async ({ page, request }) => {
  await takeQuickAssessment(page);
  const resultUrl = page.url();
  const email = uniqueEmail("coach");
  await registerAndVerify(page, request, email);

  // From the results page, the coach asks the visitor to sign in and then returns to the coach.
  await page.goto(resultUrl);
  await page.getByRole("link", { name: "Talk it through with the coach" }).click();
  await expect(page).toHaveURL(/\/login\?next=/);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "PersonalityDNA Coach" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Demo mode" })).toBeVisible();
  await expect(page.getByText("No conversations yet")).toBeVisible();
  await expectAccessible(page);

  // Consent is required.
  await page.getByLabel(/Career exploration/).check();
  await expect(page.getByLabel("Let the coach use my latest results")).toBeChecked();
  await page.getByRole("button", { name: "Start conversation" }).click();
  await expect(page.getByText("Please confirm you understand how the coach works.")).toBeVisible();
  await page.getByLabel("I understand and want to use the coach").check();
  await page.getByRole("button", { name: "Start conversation" }).click();
  await expect(page.getByRole("heading", { name: "Career exploration" })).toBeVisible();
  await expect(page.getByText("The coach can see your shared assessment results.")).toBeVisible();

  // A streamed, grounded reply.
  const box = page.getByLabel("Message the coach");
  await box.fill("How can I use my strengths at work?");
  await box.press("Enter");
  const conversation = page.getByRole("list", { name: "Conversation" });
  await expect(conversation.getByText("How can I use my strengths at work?")).toBeVisible();
  await expect(conversation.getByText(/Demo mode: this reply comes from/)).toBeVisible();
  await expect(conversation.getByText(/Your highest score is \w+ at \d+\.\d out of 100/)).toBeVisible();
  await expect(page.getByText("29 messages left today.")).toBeVisible();
  await expect(box).toHaveValue("");
  await expectAccessible(page);

  // Crisis language gets support resources instead of coaching.
  await box.fill("Some days I want to end my life");
  await page.getByRole("button", { name: "Send" }).click();
  const support = page.getByRole("note", { name: "Support is available" });
  await expect(support).toBeVisible();
  await expect(support.getByText(/call or text 988/)).toBeVisible();
  await expect(support.getByRole("link", { name: "findahelpline.com" })).toHaveAttribute(
    "href",
    "https://findahelpline.com",
  );

  // History survives a reload.
  await page.reload();
  await expect(page.getByRole("list", { name: "Conversation" }).locator(":scope > li")).toHaveCount(4);

  await page.getByRole("link", { name: "← All conversations" }).click();
  await expect(page.getByRole("link", { name: /Career exploration\s+4 messages/ })).toBeVisible();

  // Deleting removes it.
  await page.getByRole("link", { name: /Career exploration/ }).click();
  await page.getByRole("button", { name: "Delete conversation" }).click();
  await page.getByRole("group", { name: "Confirm deletion" }).getByRole("button", { name: "Delete" }).click();
  await expect(page.getByRole("heading", { name: "PersonalityDNA Coach" })).toBeVisible();
  await expect(page.getByText("No conversations yet")).toBeVisible();
});

test("coach requires an account", async ({ page }) => {
  await page.goto("/coach");
  await expect(page).toHaveURL(/\/login\?next=%2Fcoach/);
});
