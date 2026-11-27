import { expect, test, type Page } from "@playwright/test";

/**
 * Page-weight budgets for the production build. Counts the compressed bytes of every script a page
 * loads (as transferred by `next start`), so a dependency that bloats the bundle fails CI.
 * Budgets and the measured baseline are in docs/PERFORMANCE_TESTING.md.
 */
const JS_BUDGET_KB = 220;
const PAGES = ["/", "/discover", "/pricing", "/big-five", "/login", "/careers", "/account"];

async function scriptKb(page: Page, path: string): Promise<number> {
  const responses: Promise<number>[] = [];
  page.on("requestfinished", (request) => {
    if (request.resourceType() === "script") {
      responses.push(request.sizes().then((s) => s.responseBodySize));
    }
  });
  await page.goto(path, { waitUntil: "networkidle" });
  const sizes = await Promise.all(responses);
  return sizes.reduce((a, b) => a + b, 0) / 1024;
}

test.describe("page weight", () => {
  test.skip(({ isMobile }) => isMobile, "Bundles are the same on mobile; measured once on desktop.");

  for (const path of PAGES) {
    test(`${path} loads under ${JS_BUDGET_KB} KB of compressed JavaScript`, async ({ page }) => {
      const kb = await scriptKb(page, path);
      console.log(`page-weight ${path}: ${kb.toFixed(0)} KB compressed JavaScript`);
      expect(kb).toBeGreaterThan(0);
      expect(kb).toBeLessThan(JS_BUDGET_KB);
    });
  }
});
