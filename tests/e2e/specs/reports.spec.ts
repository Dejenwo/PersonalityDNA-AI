import { expect, test } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, takeQuickAssessment, uniqueEmail } from "./helpers";

test("reports: create a report, download the PDF, share a card, stop sharing and delete", async ({
  page,
  request,
  browser,
}) => {
  const email = uniqueEmail("reports");
  await registerAndVerify(page, request, email);
  await signIn(page, email);

  // Without results, the library explains what to do and creating a report is refused politely.
  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "No reports yet" })).toBeVisible();
  await expectAccessible(page);
  await page.getByRole("button", { name: "Create a new report" }).click();
  await expect(page.getByText(/Take a Big Five assessment with your account first/)).toBeVisible();

  await takeQuickAssessment(page);
  await page.goto("/history");
  await page.getByRole("link", { name: "personality report" }).click();
  await page.getByRole("button", { name: "Create a new report" }).click();

  await expect(page.getByRole("heading", { name: "Your personality report", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Big Five traits" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /^Conscientiousness: \d+ out of 100, (Lower|Middle|Higher) band$/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your development plan" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Know yourself, set a direction" })).toHaveAttribute(
    "href",
    "/growth/foundations-30",
  );
  await expect(page.getByRole("heading", { name: "Limitations" })).toBeVisible();
  await expectAccessible(page);

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF" }).click();
  expect((await download).suggestedFilename()).toMatch(/^personality-report-\d{4}-\d{2}-\d{2}\.pdf$/);

  // Share a card with bands only, open it signed out, then stop sharing.
  await page.getByLabel("Profile name and description").uncheck();
  await page.getByRole("button", { name: "Create a share link" }).click();
  const link = await page.getByLabel("Share link").inputValue();
  expect(link).toMatch(/\/card#token=[\w-]+$/);
  await expectAccessible(page);

  const visitor = await (await browser.newContext()).newPage();
  await visitor.goto(link);
  await expect(visitor.getByRole("heading", { name: "A shared personality card" })).toBeVisible();
  await expect(visitor.getByText("Personality traits", { exact: true })).toBeVisible();
  await expect(visitor.getByRole("list", { name: "Big Five trait bands" }).getByRole("listitem")).toHaveCount(5);
  await expect(visitor.getByText(email)).toHaveCount(0);
  await expectAccessible(visitor);

  await page.getByRole("button", { name: "Stop sharing" }).click();
  await expect(page.getByLabel("Share link")).toHaveCount(0);
  await visitor.reload();
  await expect(visitor.getByRole("heading", { name: "This card isn't available" })).toBeVisible();
  await visitor.context().close();

  await page.getByRole("link", { name: "Your reports" }).click();
  await expect(page.getByRole("list", { name: "Your reports" }).getByRole("listitem")).toHaveCount(1);
  await expectAccessible(page);
  await page.getByRole("link", { name: "Open report" }).click();
  await page.getByRole("button", { name: "Delete report" }).click();
  await page.getByRole("button", { name: "Yes, delete it" }).click();
  await expect(page.getByRole("heading", { name: "No reports yet" })).toBeVisible();
});
