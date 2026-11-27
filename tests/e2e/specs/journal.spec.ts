import { expect, test } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, uniqueEmail } from "./helpers";

test("journal: write, search, edit, export and delete", async ({ page, request }) => {
  await page.goto("/journal");
  await expect(page).toHaveURL(/\/login\?next=%2Fjournal/);

  const email = uniqueEmail("journal");
  await registerAndVerify(page, request, email);
  await signIn(page, email);

  await page.goto("/journal");
  await expect(page.getByRole("heading", { name: "Your journal is empty" })).toBeVisible();
  await expect(page.getByText(/never sent to the AI coach/)).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("link", { name: "Write your first entry" }).click();
  await expect(page.getByRole("heading", { name: "New entry" })).toBeVisible();
  await page.getByLabel("Gratitude").check();
  await expect(page.getByText("Write down three things you are grateful for today, however small.")).toBeVisible();
  await page.getByLabel("Title (optional)").fill("Small things");
  await page.getByLabel("Your entry").fill("Sunny walk by the river with my sister.");
  await page.getByLabel("Good", { exact: true }).check();
  await page.getByLabel("Tags (optional)").fill("Family, outdoors");
  await expectAccessible(page);
  await page.getByRole("button", { name: "Save entry" }).click();

  await expect(page.getByRole("heading", { name: "Small things", level: 1 })).toBeVisible();
  await expect(page.getByText("Sunny walk by the river with my sister.")).toBeVisible();
  await expect(page.getByText("family, outdoors")).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("button", { name: "Edit" }).click();
  await page.getByLabel("Your entry").fill("Sunny walk by the river with my sister. Then tea.");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Then tea.")).toBeVisible();

  await page.getByRole("link", { name: "← Journal" }).click();
  await page.goto("/journal/new");
  await page.getByLabel("Your entry").fill("Busy day at work, long meeting.");
  await page.getByRole("button", { name: "Save entry" }).click();
  await expect(page.getByText("Busy day at work, long meeting.")).toBeVisible();

  await page.goto("/journal");
  await expect(page.getByRole("link", { name: /Small things/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Busy day at work/ })).toBeVisible();
  await page.getByRole("searchbox", { name: "Search words" }).fill("river");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByRole("link", { name: /Busy day at work/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Small things/ })).toBeVisible();
  await page.getByRole("button", { name: "Clear" }).click();
  await expect(page.getByRole("link", { name: /Busy day at work/ })).toBeVisible();
  await expectAccessible(page);

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download as Markdown" }).click();
  expect((await download).suggestedFilename()).toMatch(/^journal-\d{4}-\d{2}-\d{2}\.md$/);

  await page.getByRole("link", { name: /Busy day at work/ }).click();
  await page.getByRole("button", { name: "Delete" }).click();
  await page.getByRole("button", { name: "Yes, delete it" }).click();
  await expect(page).toHaveURL(/\/journal$/);
  await expect(page.getByRole("link", { name: /Busy day at work/ })).toHaveCount(0);

  await page.getByRole("button", { name: "Delete all entries" }).click();
  await page.getByRole("button", { name: "Yes, delete all entries" }).click();
  await expect(page.getByRole("heading", { name: "Your journal is empty" })).toBeVisible();
});
