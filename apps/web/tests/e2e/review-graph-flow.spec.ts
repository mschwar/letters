import { expect, test } from "@playwright/test";

import { seedStoredSearch } from "./fixtures";

test("review route renders empty state without stored search", async ({ page }) => {
  await page.goto("/review");
  await expect(page.getByRole("heading", { name: "Review Queue" })).toBeVisible();
  await expect(page.getByText("Run a search from Dashboard to populate review checks.")).toBeVisible();
});

test("review and graph render populated state from stored search", async ({ page }) => {
  await seedStoredSearch(page);

  await page.goto("/review");
  await expect(page.getByText("Confidence acceptable.")).toBeVisible();
  await expect(page.getByText("Citation Audit")).toBeVisible();

  await page.getByRole("link", { name: "Graph" }).click();
  await expect(page.getByRole("heading", { name: "Relationship Graph" })).toBeVisible();
  await expect(page.locator("svg.graph")).toBeVisible();
});
