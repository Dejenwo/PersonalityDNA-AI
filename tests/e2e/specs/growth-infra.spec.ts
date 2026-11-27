import { expect, test } from "@playwright/test";
import { expectAccessible, PASSWORD, registerAndVerify, signIn, takeQuickAssessment, uniqueEmail } from "./helpers";

test("growth: referral link, notifications and preferences", async ({ browser, page, request }) => {
  // Ada has a result, finds her invite link and creates a comparison invitation.
  const ada = uniqueEmail("ada");
  await registerAndVerify(page, request, ada);
  await signIn(page, ada);
  await takeQuickAssessment(page);
  await page.goto("/account");
  const referral = await page.getByLabel("Your invite link").inputValue();
  expect(referral).toMatch(/\/\?ref=[A-Za-z0-9]{8}$/);
  await expect(page.getByText("0 people have joined with your link.")).toBeVisible();
  await expect(page.getByText(/never who they are/)).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("link", { name: "Notifications", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Notifications", level: 1 })).toBeVisible();
  await expect(page.getByText("Nothing here yet")).toBeVisible();
  await expectAccessible(page);

  await page.goto("/relationships");
  await page.getByLabel(/I agree to show the person who accepts/).check();
  await page.getByRole("button", { name: "Create invitation link" }).click();
  const invite = await page.getByLabel("Your invitation link").inputValue();

  // Bob arrives through Ada's referral link, signs up, then accepts the invitation.
  const bobPage = await (await browser.newContext()).newPage();
  const code = new URL(referral).searchParams.get("ref")!;
  await bobPage.goto(`/?ref=${code}&utm_source=e2e`);
  await expect(bobPage.getByRole("heading", { level: 1 })).toBeVisible();
  const bob = uniqueEmail("bob");
  await registerAndVerify(bobPage, request, bob);
  await bobPage.goto(invite);
  await bobPage.getByLabel("Email").fill(bob);
  await bobPage.getByLabel("Password").fill(PASSWORD);
  await bobPage.getByRole("button", { name: "Sign in" }).click();
  await bobPage.getByLabel(/I agree to show your partner/).check();
  await bobPage.getByRole("button", { name: "Accept invitation" }).click();
  await expect(bobPage.getByRole("heading", { name: "You and your partner" })).toBeVisible();

  // Ada sees the count and an unread notification that names no private content.
  await page.goto("/account");
  await expect(page.getByText("1 person has joined with your link.")).toBeVisible();
  await expect(page.getByText(bob)).toHaveCount(0);
  await page.getByRole("link", { name: "Notifications, 1 unread" }).click();
  await expect(page.getByRole("heading", { name: "Inbox (1 unread)" })).toBeVisible();
  await expect(page.getByRole("listitem").getByText("Unread: Your invitation to compare was accepted")).toBeVisible();
  await page.getByRole("button", { name: /Mark as read/ }).click();
  await expect(page.getByRole("heading", { name: "Inbox", exact: true })).toBeVisible();

  // Preferences: security can't be switched off; relationship emails can.
  const prefs = page.getByRole("table", { name: "Notification preferences" });
  await expect(prefs.getByLabel("Security: email")).toBeDisabled();
  await expect(prefs.getByLabel("News and tips: email")).not.toBeChecked();
  await prefs.getByLabel("Relationships: email").click();
  await expect(page.getByText("Saved your choice for relationships.")).toBeVisible();
  await expect(prefs.getByLabel("Relationships: email")).not.toBeChecked();
  await page.reload();
  await expect(page.getByRole("table", { name: "Notification preferences" }).getByLabel("Relationships: email")).not.toBeChecked();
  await expectAccessible(page);
});

test("seo: Big Five article, sitemap and robots", async ({ page, request }) => {
  await page.goto("/big-five");
  await expect(page.getByRole("heading", { name: "The Big Five personality traits", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /\/big-five$/);
  await expectAccessible(page);

  const sitemap = await (await request.get("/sitemap.xml")).text();
  expect(sitemap).toContain("/big-five</loc>");
  expect(sitemap).not.toContain("/account");
  const robots = await (await request.get("/robots.txt")).text();
  expect(robots).toContain("Disallow: /admin");
  expect(robots).toContain("Disallow: /journal");
  expect(robots).toMatch(/Sitemap: .+\/sitemap\.xml/);
});
