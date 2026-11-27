import { expect, test } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, uniqueEmail } from "./helpers";

test("emotional awareness: hub, module, progress and support note", async ({ page, request }) => {
  await page.goto("/learn");
  await expect(page.getByRole("heading", { name: "Learn", level: 1 })).toBeVisible();
  await expectAccessible(page);
  await page.getByRole("link", { name: /Emotional awareness/ }).click();
  await expect(page.getByRole("heading", { name: "Emotional awareness", level: 1 })).toBeVisible();
  await expect(page.getByText(/there is no emotional intelligence score/)).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Getting support" })).toContainText("988");
  await expect(page.getByText("to keep track of the activities you finish.")).toBeVisible();
  await expectAccessible(page);

  const email = uniqueEmail("ea");
  await registerAndVerify(page, request, email);
  await signIn(page, email);

  await page.goto("/emotional-awareness");
  await page.getByRole("link", { name: /Listening to understand/ }).click();
  await expect(page.getByRole("heading", { name: "Listening to understand", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Check before you fix" })).toBeVisible();
  await page.getByRole("button", { name: 'Mark "Ask: ideas or an ear?" as done' }).click();
  await expect(page.getByRole("button", { name: 'Mark "Ask: ideas or an ear?" as not done' })).toBeVisible();
  await expect(page.getByRole("link", { name: "Reflect with the coach" })).toHaveAttribute(
    "href",
    "/coach?topic=emotions",
  );
  await expectAccessible(page);

  await page.getByRole("link", { name: "← Emotional awareness" }).click();
  await expect(page.getByRole("link", { name: /Listening to understand.*1 of 2 activities done/ })).toBeVisible();
});
