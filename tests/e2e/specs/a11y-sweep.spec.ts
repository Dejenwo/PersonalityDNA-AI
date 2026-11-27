import { expect, test, type Page } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, takeQuickAssessment, uniqueEmail } from "./helpers";

// Every screen, checked with axe (WCAG 2.2 AA) in light and dark mode. Flows are tested in the other specs;
// this sweep catches screens or colour schemes those flows don't reach. It also checks basic page quality:
// one h1, nothing wider than the screen, and no script errors in the console.
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
  "/feedback",
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

// Signed out, restoring a session answers 401 by design; the browser logs that as a failed request.
const EXPECTED_ERRORS = [/status of 401/];

async function sweep(page: Page, paths: string[]) {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" && !EXPECTED_ERRORS.some((re) => re.test(m.text()))) errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  for (const scheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: scheme, reducedMotion: "reduce" });
    for (const path of paths) {
      await test.step(`${path} (${scheme})`, async () => {
        errors.length = 0;
        await page.goto(path);
        await expect(page.locator("main")).toBeVisible();
        // Wait until loading states have settled.
        await expect(page.locator("[role=status]", { hasText: "…" })).toHaveCount(0);
        await expectAccessible(page);
        if (scheme === "light") {
          await expect(page.locator("h1")).toHaveCount(1);
          const width = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
          expect(width, "page is wider than the screen").toBeLessThanOrEqual(0);
          // The missing-page check is meant to answer 404.
          const unexpected = path === "/this-page-does-not-exist" ? errors.filter((e) => !/status of 404/.test(e)) : errors;
          expect(unexpected, "console errors").toEqual([]);
        }
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
