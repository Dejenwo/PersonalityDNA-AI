import { expect, test } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, uniqueEmail } from "./helpers";

test("pricing: plans are clear, subscribe with the local checkout, then cancel", async ({ page, request }) => {
  await page.goto("/pricing");
  await expect(page.getByRole("heading", { name: "Plans and pricing", level: 1 })).toBeVisible();
  const plans = page.getByRole("list", { name: "Plans" });
  await expect(plans.getByRole("heading", { name: "Free" })).toBeVisible();
  await expect(plans.getByText("$9.99 a month")).toBeVisible();
  await expect(plans.getByText("$69.99 a year")).toBeVisible();
  await expect(page.getByText("About 41% less than paying monthly for a year.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Create an account to subscribe" }).first()).toBeVisible();
  await expectAccessible(page);

  const email = uniqueEmail("pricing");
  await registerAndVerify(page, request, email);
  await signIn(page, email);
  await page.goto("/account");
  await expect(page.getByText("During the preview, every feature is available to every account.")).toBeVisible();
  await page.getByRole("link", { name: "See plans" }).click();

  await page.getByRole("button", { name: "Choose Premium monthly" }).click();
  await expect(page).toHaveURL(/\/account\?checkout=success$/);
  await expect(page.getByText(/^Premium monthly, renews on /)).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("button", { name: "Manage or cancel subscription" }).click();
  await expect(page.getByText(/^Premium monthly ends on .+ It won't renew\.$/)).toBeVisible();

  await page.goto("/pricing");
  await expect(page.getByText("Your current plan")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Choose / })).toHaveCount(0);
});
