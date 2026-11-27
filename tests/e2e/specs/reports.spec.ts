import { expect, test } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, takeQuickAssessment, uniqueEmail } from "./helpers";

test("reports: create a report from results, read it, download the PDF and delete it", async ({ page, request }) => {
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

  await page.getByRole("link", { name: "Your reports" }).click();
  await expect(page.getByRole("list", { name: "Your reports" }).getByRole("listitem")).toHaveCount(1);
  await expectAccessible(page);
  await page.getByRole("link", { name: "Open report" }).click();
  await page.getByRole("button", { name: "Delete report" }).click();
  await page.getByRole("button", { name: "Yes, delete it" }).click();
  await expect(page.getByRole("heading", { name: "No reports yet" })).toBeVisible();
});
