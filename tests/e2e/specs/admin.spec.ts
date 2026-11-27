import { expect, test } from "@playwright/test";
import { expectAccessible, grantAdminRole, registerAndVerify, signIn, uniqueEmail } from "./helpers";

test("admin: hidden from members, overview, account support actions, content and audit", async ({
  page: memberPage,
  request,
  browser,
}) => {
  const member = uniqueEmail("member");
  await registerAndVerify(memberPage, request, member);
  await signIn(memberPage, member);
  await memberPage.goto("/admin");
  await expect(memberPage.getByRole("heading", { name: "Page not found" })).toBeVisible();

  const admin = uniqueEmail("admin");
  const page = await (await browser.newContext()).newPage();
  await registerAndVerify(page, request, admin);
  grantAdminRole(admin, "superadmin");
  await signIn(page, admin);
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Administration", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "System health" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Accounts and activity" })).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("button", { name: "Accounts" }).click();
  await page.getByLabel("Email or account id").fill(member);
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("list", { name: "Accounts" }).getByRole("button", { name: new RegExp(member) }).click();
  await expect(page.getByRole("heading", { name: member })).toBeVisible();
  await expect(page.getByText("Journals, coaching conversations, answers and report contents are never shown here.")).toBeVisible();
  await page.getByLabel("Reason (kept in the audit log)").fill("Support request");
  await page.getByRole("button", { name: "Grant complimentary Premium" }).click();
  await expect(page.getByText("Complimentary Premium granted.")).toBeVisible();
  await expect(page.getByText(/premium-monthly via manual, active/)).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("button", { name: "Content" }).click();
  await expect(page.getByRole("heading", { name: "Instruments" })).toBeVisible();
  await expect(page.getByText(/mini-ipip-20/).first()).toBeVisible();

  await page.getByRole("button", { name: "Audit log" }).click();
  await page.getByLabel("Event type starts with").fill("admin.");
  await page.getByRole("button", { name: "Filter" }).click();
  await expect(page.getByText("Admin: subscription granted").first()).toBeVisible();
  await expect(page.getByText("Admin: role granted").first()).toBeVisible();
  await expectAccessible(page);
});
