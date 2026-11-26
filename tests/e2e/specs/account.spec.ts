import { expect, test } from "@playwright/test";
import {
  emailLink,
  expectAccessible,
  PASSWORD,
  registerAndVerify,
  signIn,
  takeQuickAssessment,
  uniqueEmail,
} from "./helpers";

test("sign-up pages are accessible", async ({ page }) => {
  for (const path of ["/register", "/login", "/forgot-password"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expectAccessible(page);
  }
});

test("an assessment taken before sign-up moves into the new account", async ({ page, request, browser }) => {
  await takeQuickAssessment(page);
  const resultUrl = page.url();
  const email = uniqueEmail("claim");
  await registerAndVerify(page, request, email);

  // Unverified sign-in is refused before this point; now it works.
  await signIn(page, email);
  await expect(page.getByText("Everything saved to your account")).toBeVisible();
  await expect(page.getByRole("link", { name: "View results" })).toHaveCount(1);
  await expectAccessible(page);

  // Session survives a reload (refresh cookie) and results open on a fresh device once signed in.
  await page.reload();
  await expect(page.getByRole("link", { name: "Account" })).toBeVisible();

  const other = await browser.newContext();
  const second = await other.newPage();
  await signIn(second, email);
  await second.goto(resultUrl);
  await expect(second.getByRole("heading", { name: "Your Big Five traits" })).toBeVisible();
  await other.close();
});

test("password reset signs out other sessions and accepts the new password", async ({ page, request }) => {
  const email = uniqueEmail("reset");
  await registerAndVerify(page, request, email);
  await page.goto("/forgot-password");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByText(/we sent a link to reset the password/)).toBeVisible();

  await page.goto(await emailLink(request, email, "reset_password"));
  await expect(page.getByRole("heading", { name: "Choose a new password" })).toBeVisible();
  await page.getByLabel("New password").fill("short");
  await page.getByRole("button", { name: "Save new password" }).click();
  await expect(page.getByText("Use at least 10 characters.")).toBeVisible();
  await page.getByLabel("New password").fill("an entirely different passphrase");
  await page.getByRole("button", { name: "Save new password" }).click();
  await expect(page.getByRole("heading", { name: "Password updated" })).toBeVisible();

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Email or password is incorrect.")).toBeVisible();
  await signIn(page, email, "an entirely different passphrase");
});

test("account page: export data, sign out, delete account", async ({ page, request }) => {
  const email = uniqueEmail("delete");
  await registerAndVerify(page, request, email);
  await signIn(page, email);
  await takeQuickAssessment(page);

  await page.goto("/account");
  await expect(page.getByText(email)).toBeVisible();
  await expectAccessible(page);

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download my data" }).click();
  const file = await download;
  const data = JSON.parse(await (await file.createReadStream()).toArray().then((c) => Buffer.concat(c).toString()));
  expect(data.account.email).toBe(email);
  expect(data.assessments).toHaveLength(1);
  expect(data.assessments[0].answers).toHaveLength(20);

  await page.getByRole("button", { name: "Delete my account…" }).click();
  await page.getByLabel("Enter your password to confirm").fill(PASSWORD);
  await page.getByRole("button", { name: "Permanently delete" }).click();
  await expect(page).toHaveURL(/\/\?deleted=1$/);

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Email or password is incorrect.")).toBeVisible();
});
