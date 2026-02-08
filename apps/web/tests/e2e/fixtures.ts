import type { Page } from "@playwright/test";

export const STORE_KEY = "letterops.latest_search";

export const STORED_SEARCH = {
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

export async function seedStoredSearch(page: Page): Promise<void> {
  await page.addInitScript(([key, value]) => {
    window.localStorage.setItem(key, value);
  }, [STORE_KEY, JSON.stringify(STORED_SEARCH)]);
}
