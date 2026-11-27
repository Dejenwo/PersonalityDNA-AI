import { expect, test } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, uniqueEmail } from "./helpers";

test("goals and habits: create, milestones, daily check, pause and adjust", async ({ page, request }) => {
  const email = uniqueEmail("goals");
  await registerAndVerify(page, request, email);
  await signIn(page, email);

  await page.goto("/goals");
  await expect(page.getByRole("heading", { name: "Goals and habits", level: 1 })).toBeVisible();
  await expect(page.getByText("No habits yet.")).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("button", { name: "Add a goal" }).click();
  await page.getByLabel("Goal", { exact: true }).fill("Run a 5k");
  await page.getByLabel("Why it matters to you (optional)").fill("To feel stronger");
  await page.getByLabel("Milestones (optional)").fill("Run 1k\nRun 3k");
  await page.getByRole("button", { name: "Save goal" }).click();
  await expect(page.getByRole("link", { name: /Run a 5k.*0 of 2 milestones done/ })).toBeVisible();

  await page.getByRole("button", { name: "Add a habit" }).click();
  await page.getByLabel("Habit", { exact: true }).fill("Stretch for 5 minutes");
  await page.getByLabel("Supports a goal (optional)").selectOption({ label: "Run a 5k" });
  await expectAccessible(page);
  await page.getByRole("button", { name: "Save habit" }).click();
  await page.getByRole("button", { name: "Mark done today: Stretch for 5 minutes" }).click();
  await expect(page.getByRole("button", { name: "Done today: Stretch for 5 minutes" })).toBeVisible();
  await expect(page.getByText("Done on 1 of 1 planned day in the last 30 days.")).toBeVisible();
  await page.getByText("History and settings").click();
  await expect(page.getByRole("list", { name: "Last four weeks" }).getByText(/: done$/)).toHaveCount(1);
  await expectAccessible(page);

  await page.reload();
  await expect(page.getByRole("button", { name: "Done today: Stretch for 5 minutes" })).toBeVisible();
  await page.getByText("History and settings").click();
  await page.getByRole("button", { name: "Pause habit" }).click();
  await expect(page.getByText("Paused habits (1)")).toBeVisible();

  await page.getByRole("link", { name: /Run a 5k/ }).click();
  await expect(page.getByRole("heading", { name: "Run a 5k", level: 1 })).toBeVisible();
  await expect(page.getByText("Why it matters: To feel stronger")).toBeVisible();
  await page.getByLabel("Run 1k").check();
  await expect(page.getByText("1 of 2 done")).toBeVisible();
  await page.getByLabel("New milestone").fill("Run 5k");
  await page.getByRole("button", { name: "Add milestone" }).click();
  await expect(page.getByText("1 of 3 done")).toBeVisible();
  await expect(page.getByRole("link", { name: "Write a goal reflection" })).toHaveAttribute("href", "/journal/new?kind=goal");
  await expectAccessible(page);

  await page.getByRole("button", { name: "Adjust goal" }).click();
  await page.getByLabel("Goal", { exact: true }).fill("Run a 10k");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { name: "Run a 10k", level: 1 })).toBeVisible();
  await page.getByRole("button", { name: "Mark goal complete" }).click();
  await expect(page.getByText(/^Completed/)).toBeVisible();

  await page.getByRole("button", { name: "Delete goal" }).click();
  await page.getByRole("button", { name: "Yes, delete the goal" }).click();
  await expect(page).toHaveURL(/\/goals$/);
  await expect(page.getByText("No goals yet.", { exact: false })).toBeVisible();
});
