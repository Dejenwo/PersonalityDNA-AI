import { expect, test } from "@playwright/test";
import { expectAccessible, grantAdminRole, registerAndVerify, signIn, uniqueEmail } from "./helpers";

test("feedback: send anonymously from any page, send signed in, support triages", async ({ page, request, browser }) => {
  const run = Date.now().toString(36);
  await page.goto("/pricing");
  await page.getByRole("link", { name: "Send feedback" }).click();
  await expect(page.getByRole("heading", { name: "Send feedback", level: 1 })).toBeVisible();
  await expect(page.getByText("We'll note that you came from /pricing.")).toBeVisible();
  await expect(page.getByText(/sent anonymously/)).toBeVisible();
  await expectAccessible(page);
  await page.getByRole("button", { name: "Send feedback" }).click();
  await expect(page.getByText("Please write at least 10 characters")).toBeVisible();
  await page.getByLabel("Wording or content").check();
  await page.getByLabel("Your message").fill(`The yearly price is hard to find on small screens (${run}).`);
  await page.getByRole("button", { name: "Send feedback" }).click();
  await expect(page.getByText("Thank you. We've received your feedback.")).toBeVisible();

  const person = uniqueEmail("feedback");
  await registerAndVerify(page, request, person);
  await signIn(page, person);
  await page.goto("/feedback");
  await page.getByLabel("Your message").fill(`Question 12 skipped ahead when I pressed Back (${run}).`);
  await page.getByLabel(/You may contact me/).check();
  await page.getByRole("button", { name: "Send feedback" }).click();
  await expect(page.getByText("Thank you. We've received your feedback.")).toBeVisible();
  const sent = page.getByRole("region", { name: "What you've sent" });
  await expect(sent.getByText(`Question 12 skipped ahead when I pressed Back (${run}).`)).toBeVisible();
  await expect(sent.getByText("Received")).toBeVisible();
  await expectAccessible(page);

  const support = uniqueEmail("support");
  const admin = await (await browser.newContext()).newPage();
  await registerAndVerify(admin, request, support);
  grantAdminRole(support, "support");
  await signIn(admin, support);
  await admin.goto("/admin");
  await admin.getByRole("button", { name: "Feedback" }).click();
  const list = admin.getByRole("list", { name: "Feedback" });
  const item = list.getByRole("listitem").filter({ hasText: `Back (${run})` });
  await expect(item.getByText(/account [0-9a-f-]{36}/)).toBeVisible();
  await expect(list.getByRole("listitem").filter({ hasText: `small screens (${run})` }).getByText(/anonymous/)).toBeVisible();
  await expectAccessible(admin);
  await item.getByLabel("Status").selectOption("fixed");
  await expect(item.getByLabel("Status")).toHaveValue("fixed");

  await page.reload();
  await expect(page.getByRole("region", { name: "What you've sent" }).getByText("Fixed")).toBeVisible();
});
