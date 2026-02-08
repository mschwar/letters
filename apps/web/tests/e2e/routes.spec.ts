import { expect, test } from "@playwright/test";

const STORE_KEY = "letterops.latest_search";

const STORED_SEARCH = {
  query: "guidance regarding family life and marriage",
  at: "2026-02-08T05:00:00.000Z",
  meta: {
    retrieval_mode: "hybrid",
    sort_by: "relevance"
  },
  payload: {
    query: "guidance regarding family life and marriage",
    answer: "Sample synthesized answer with [1] citation.",
    confidence: { score: 0.74, label: "medium" },
    citations: [
      {
        ref: "[1]",
        document_id: "doc-1",
        title: "Message to the Bahais of the World",
        source_name: "Universal House of Justice",
        document_date: "1984-01-02",
        snippet: "Marriage in the Baha'i teachings is a fortress for well-being.",
        score: 0.99
      }
    ],
    results: [
      {
        document_id: "doc-1",
        title: "Message to the Bahais of the World",
        source_name: "Universal House of Justice",
        document_date: "1984-01-02",
        summary: "A summary about family life and marriage guidance.",
        snippet: "Marriage in the Baha'i teachings is a fortress for well-being.",
        score: 0.99
      }
    ]
  }
};

test("dashboard route renders core controls", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Operational Reading Console" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Session" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Retrieval" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Run Search" })).toBeVisible();
});

test("review route renders empty state without stored search", async ({ page }) => {
  await page.goto("/review");
  await expect(page.getByRole("heading", { name: "Review Queue" })).toBeVisible();
  await expect(page.getByText("Run a search from Dashboard to populate review checks.")).toBeVisible();
});

test("review and graph routes render populated state from stored search", async ({ page }) => {
  await page.addInitScript(([key, value]) => {
    window.localStorage.setItem(key, value);
  }, [STORE_KEY, JSON.stringify(STORED_SEARCH)]);

  await page.goto("/review");
  await expect(page.getByText("Confidence acceptable.")).toBeVisible();
  await expect(page.getByText("Citation Audit")).toBeVisible();

  await page.getByRole("link", { name: "Graph" }).click();
  await expect(page.getByRole("heading", { name: "Relationship Graph" })).toBeVisible();
  await expect(page.locator("svg.graph")).toBeVisible();
});
