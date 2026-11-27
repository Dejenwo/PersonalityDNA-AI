import { expect, test } from "@playwright/test";
import { expectAccessible, grantAdminRole, PASSWORD, registerAndVerify, signIn, uniqueEmail } from "./helpers";

test("organisations: create, invite, join voluntarily, programmes, statistics stay hidden, licence", async ({
  browser,
  page,
  request,
}) => {
  // Olu starts an organisation.
  const olu = uniqueEmail("olu");
  await registerAndVerify(page, request, olu);
  await signIn(page, olu);
  await page.goto("/orgs");
  await expect(page.getByRole("heading", { name: "Organisations", level: 1 })).toBeVisible();
  await expect(page.getByText("You're not in any organisation")).toBeVisible();
  await expectAccessible(page);
  const orgName = `Team ${Date.now()}`;
  await page.getByRole("textbox", { name: "Name", exact: true }).fill(orgName);
  await page.getByRole("button", { name: "Create organisation" }).click();
  await expect(page.getByText("Please confirm how organisations work.")).toBeVisible();
  await page.getByLabel(/I understand that taking part is voluntary/).check();
  await page.getByRole("button", { name: "Create organisation" }).click();
  await expect(page.getByRole("heading", { name: orgName, level: 1 })).toBeVisible();
  await expect(page.getByText(/1 of 25 seats used/)).toBeVisible();

  // A programme built from the versioned content.
  await page.getByRole("textbox", { name: "Title", exact: true }).fill("Spring cohort");
  await page.getByLabel("Growth programme").selectOption({ index: 1 });
  await page.getByRole("button", { name: "Create programme" }).click();
  await expect(page.getByRole("heading", { name: "Spring cohort" })).toBeVisible();
  await expect(page.getByText(/Group statistics appear once at least 10 members/)).toBeVisible();
  await expectAccessible(page);

  await page.getByLabel("How many people can use it").fill("5");
  await page.getByRole("button", { name: "Create join link" }).click();
  const link = await page.getByLabel("Join link").inputValue();
  expect(link).toMatch(/\/orgs\/join#token=[\w-]+$/);
  await expect(page.getByText(/Member link · 0 of 5 used/)).toBeVisible();

  // Mia opens the link signed out, signs in and decides to join.
  const miaPage = await (await browser.newContext()).newPage();
  const mia = uniqueEmail("mia");
  await registerAndVerify(miaPage, request, mia);
  await miaPage.goto(link);
  await expect(miaPage).toHaveURL(/\/login\?next=/);
  await miaPage.getByLabel("Email").fill(mia);
  await miaPage.getByLabel("Password").fill(PASSWORD);
  await miaPage.getByRole("button", { name: "Sign in" }).click();
  await expect(miaPage.getByRole("heading", { name: `Join ${orgName}` })).toBeVisible();
  expect(miaPage.url()).not.toContain("token=");
  await expect(miaPage.getByText(/never sees your answers, results/)).toBeVisible();
  await expectAccessible(miaPage);
  await miaPage.getByLabel(/can see my name, email, role and join date/).check();
  await miaPage.getByRole("button", { name: "Join organisation" }).click();
  await expect(miaPage.getByRole("heading", { name: orgName, level: 1 })).toBeVisible();
  await expect(miaPage.getByText("You're a member.", { exact: false })).toBeVisible();
  // Members don't get the management panels.
  await expect(miaPage.getByRole("heading", { name: "Members" })).toHaveCount(0);
  await miaPage.getByRole("button", { name: "Join programme" }).click();
  await expect(miaPage.getByText("Joined", { exact: true })).toBeVisible();
  await miaPage.getByLabel(/Include my latest Big Five bands/).check();
  await expect(miaPage.getByLabel(/Include my latest Big Five bands/)).toBeChecked();
  await expectAccessible(miaPage);

  // Olu sees Mia's name and email, but not her choices: one participant is below the threshold.
  await page.reload();
  const members = page.getByRole("region", { name: "Members" });
  await expect(members.getByText(mia)).toBeVisible();
  await expect(page.getByText("Spring cohort: fewer than 3 joined")).toBeVisible();
  await expect(page.getByText("Fewer than 10")).toBeVisible();

  // A superadmin records a licence; Mia's plan becomes the organisation licence.
  const root = uniqueEmail("root");
  const rootPage = await (await browser.newContext()).newPage();
  await registerAndVerify(rootPage, request, root);
  grantAdminRole(root, "superadmin");
  await signIn(rootPage, root);
  await rootPage.goto("/admin");
  await rootPage.getByRole("button", { name: "Organisations" }).click();
  await rootPage.getByLabel("Name or ID").fill(orgName);
  await rootPage.getByRole("button", { name: "Search" }).click();
  await expect(rootPage.getByText(orgName)).toBeVisible();
  await rootPage.getByLabel("Reason (audited)").fill("Signed pilot agreement");
  await rootPage.getByRole("button", { name: "Save licence" }).click();
  await expect(rootPage.getByText("Licence saved.")).toBeVisible();
  await expect(rootPage.getByText(/licensed until/)).toBeVisible();
  await expectAccessible(rootPage);

  await miaPage.reload();
  await expect(miaPage.getByText(/Licensed: members have Premium features/)).toBeVisible();

  // Mia leaves; she no longer sees the organisation.
  await miaPage.getByRole("button", { name: "Leave organisation" }).click();
  await miaPage.getByRole("button", { name: "Yes, leave" }).click();
  await expect(miaPage.getByRole("heading", { name: "Organisations", level: 1 })).toBeVisible();
  await expect(miaPage.getByText("You're not in any organisation")).toBeVisible();
});
