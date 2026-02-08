import { expect, test } from "@playwright/test";

import { seedStoredSearch } from "./fixtures";

test("root route redirects to dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Operational Reading Console" })).toBeVisible();
});

test("nav chips switch between dashboard, review, and graph", async ({ page }) => {
  await seedStoredSearch(page);
  await page.goto("/dashboard");

  await page.getByRole("link", { name: "Review" }).click();
  await expect(page).toHaveURL(/\/review$/);
  await expect(page.getByRole("heading", { name: "Review Queue" })).toBeVisible();

  await page.getByRole("link", { name: "Graph" }).click();
  await expect(page).toHaveURL(/\/graph$/);
  await expect(page.getByRole("heading", { name: "Relationship Graph" })).toBeVisible();

  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Retrieval" })).toBeVisible();
});
