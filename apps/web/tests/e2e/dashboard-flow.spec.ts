import { expect, test } from "@playwright/test";

test("dashboard login success flow shows authenticated status", async ({ page }) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: { ok: true } })
    });
  });

  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page.getByText("Authenticated. Session cookie active.")).toBeVisible();
});

test("dashboard login failure surfaces API detail", async ({ page }) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "invalid credentials" })
    });
  });

  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page.getByText("Auth failed: invalid credentials")).toBeVisible();
});

test("dashboard search flow syncs form inputs into URL params", async ({ page }) => {
  await page.goto("/dashboard");

  await page.getByLabel("Query").fill("family consultation guidance");
  await page.getByLabel("Source").fill("Universal House of Justice");
  await page.getByLabel("Tag").fill("family");
  await page.getByLabel("Date from").fill("1980-01-01");
  await page.getByLabel("Date to").fill("1990-12-31");
  await page.getByLabel("Limit").fill("7");
  await page.getByLabel("Sort").selectOption("date_desc");

  await page.getByRole("button", { name: "Run Search" }).click();
  await expect(page).toHaveURL(/\/dashboard\?/);
  await expect(page).toHaveURL(/q=family\+consultation\+guidance/);
  await expect(page).toHaveURL(/source=Universal\+House\+of\+Justice/);
  await expect(page).toHaveURL(/tag=family/);
  await expect(page).toHaveURL(/from=1980-01-01/);
  await expect(page).toHaveURL(/to=1990-12-31/);
  await expect(page).toHaveURL(/limit=7/);
  await expect(page).toHaveURL(/sort=date_desc/);
});
