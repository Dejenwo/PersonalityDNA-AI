import { expect, test } from "@playwright/test";
import { expectAccessible, registerAndVerify, signIn, uniqueEmail } from "./helpers";

// The e2e build sets NEXT_PUBLIC_I18N_PREVIEW=true, which offers pseudo-locales for layout testing.
test("languages: English by default, right-to-left layout, choice remembered, profile language", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  const select = page.getByLabel("Language", { exact: true });
  await expect(select).toHaveValue("en");

  await select.selectOption("ar-XB");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("lang", "ar-XB");
  const nav = page.getByRole("navigation").first();
  await expect(nav.getByRole("link", { name: /Ðíšçóṽéŕ/ })).toBeVisible();
  await expectAccessible(page);

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await page.getByRole("combobox").last().selectOption("en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.getByRole("link", { name: "Discover" })).toBeVisible();

  const ada = uniqueEmail("lang");
  await registerAndVerify(page, request, ada);
  await signIn(page, ada);
  await page.goto("/account");
  await expect(page.getByRole("heading", { name: "Language", level: 2 })).toBeVisible();
  await expect(page.getByLabel("Display language")).toHaveValue("en");
  await expectAccessible(page);
});
