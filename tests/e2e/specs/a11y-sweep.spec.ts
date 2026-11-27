import { expect, test, type Page } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, takeQuickAssessment, uniqueEmail } from "./helpers";

// Every screen, checked with axe (WCAG 2.2 AA) in light and dark mode. Flows are tested in the other specs;
// this sweep catches screens or colour schemes those flows don't reach.
const PUBLIC = [
  "/",
  "/big-five",
  "/discover",
  "/discover/mini-ipip-20",
  "/learn",
  "/growth",
  "/growth/confidence-7",
  "/emotional-awareness",
  "/leadership",
  "/careers",
  "/pricing",
  "/privacy",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
  "/card",
  "/relationships/join",
  "/orgs/join",
  "/this-page-does-not-exist",
];

const SIGNED_IN = [
  "/history",
  "/account",
  "/notifications",
  "/coach",
  "/journal",
  "/journal/new",
  "/goals",
  "/relationships",
  "/reports",
  "/orgs",
];

async function sweep(page: Page, paths: string[]) {
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
    for (const path of paths) {
      await test.step(`${path} (${scheme})`, async () => {
        await page.goto(path);
        await expect(page.locator("main")).toBeVisible();
        // Wait until loading states have settled.
        await expect(page.locator("[role=status]", { hasText: "…" })).toHaveCount(0);
        await expectAccessible(page);
      });
    }
  }
}

test("accessibility sweep: public screens, light and dark", async ({ page }) => {
  await sweep(page, PUBLIC);
});

test("accessibility sweep: signed-in screens, light and dark", async ({ page, request }) => {
  const email = uniqueEmail("sweep");
  await registerAndVerify(page, request, email);
  await signIn(page, email);
  await takeQuickAssessment(page);
  const result = page.url();
  await sweep(page, [...SIGNED_IN, new URL(result).pathname]);
});
