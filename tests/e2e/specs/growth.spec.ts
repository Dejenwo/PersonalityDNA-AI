import { expect, test } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, uniqueEmail } from "./helpers";

test("growth: browse, start a challenge, mark days, self-check and leave", async ({ page, request }) => {
  await page.goto("/learn");
  await page.getByRole("link", { name: /Growth programmes/ }).click();
  await expect(page.getByRole("heading", { name: "Growth programmes", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "7-day challenges" })).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("link", { name: /Ninety days of personal growth/ }).click();
  await expect(page.getByRole("heading", { name: "Ninety days of personal growth", level: 1 })).toBeVisible();
  await expect(page.getByText("Week 12: Review and plan ahead")).toBeVisible();
  await expect(page.getByText("to start the programme and keep track of your days.")).toBeVisible();
  await expectAccessible(page);

  const email = uniqueEmail("growth");
  await registerAndVerify(page, request, email);
  await signIn(page, email);

  await page.goto("/growth/confidence-7");
  await page.getByRole("button", { name: "Start the programme" }).click();
  await expect(page.getByText("0 of 7 days done · next: day 1")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Next up: Day 1 · Learn" })).toBeVisible();
  await page.getByRole("button", { name: "I've done today's exercise" }).click();
  await expect(page.getByText("1 of 7 days done · next: day 2")).toBeVisible();
  await page.getByRole("button", { name: "Mark day 3 as done" }).click();
  await expect(page.getByRole("button", { name: "Mark day 3 as not done" })).toBeVisible();
  await page.getByRole("radio", { name: "Quite a lot" }).check();
  await expect(page.getByRole("radio", { name: "Quite a lot" })).toBeChecked();
  await expectAccessible(page);

  // Progress is saved on the server.
  await page.reload();
  await expect(page.getByText("2 of 7 days done · next: day 2")).toBeVisible();
  await expect(page.getByRole("radio", { name: "Quite a lot" })).toBeChecked();
  await page.goto("/growth");
  await expect(page.getByRole("heading", { name: "Your programmes" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Seven days of small brave steps.*2 of 7 days done/ }).first()).toBeVisible();

  await page.goto("/growth/confidence-7");
  await page.getByRole("button", { name: "Leave programme" }).click();
  await page.getByRole("button", { name: "Yes, leave" }).click();
  await expect(page.getByRole("button", { name: "Start the programme" })).toBeVisible();
});
