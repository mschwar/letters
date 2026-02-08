import { cookies } from "next/headers";

import { DashboardClient } from "../../components/dashboard-client";
import { searchServer, type SearchRequest, type SearchResponse } from "../../lib/api";

type RawParams = Record<string, string | string[] | undefined>;

function first(raw: string | string[] | undefined): string {
  if (!raw) return "";
  return Array.isArray(raw) ? raw[0] ?? "" : raw;
}

function parseSort(raw: string): SearchRequest["sort_by"] {
  if (raw === "date_desc" || raw === "date_asc") return raw;
  return "relevance";
}

function parseLimit(raw: string): number {
  const value = Number(raw);
  if (Number.isFinite(value)) {
    return Math.max(1, Math.min(20, Math.trunc(value)));
  }
  return 5;
}

function formFromParams(searchParams: RawParams) {
  return {
    query: first(searchParams.q) || "guidance regarding family life and marriage",
    sourceName: first(searchParams.source),
    tag: first(searchParams.tag),
    dateFrom: first(searchParams.from),
    dateTo: first(searchParams.to),
    limit: parseLimit(first(searchParams.limit)),
    sortBy: parseSort(first(searchParams.sort))
  };
}

function requestFromForm(form: ReturnType<typeof formFromParams>): SearchRequest | null {
  if (!form.query.trim()) return null;
  return {
    query: form.query.trim(),
    limit: form.limit,
    source_name: form.sourceName.trim() || undefined,
    tag: form.tag.trim() || undefined,
    date_from: form.dateFrom || undefined,
    date_to: form.dateTo || undefined,
    sort_by: form.sortBy
  };
}

export default async function DashboardPage({
  searchParams
}: {
  searchParams?: Promise<RawParams>;
}) {
  const params = (await searchParams) ?? {};
  const form = formFromParams(params);
  const request = requestFromForm(form);

  let initialResult: SearchResponse | null = null;
  let initialStatus = "Run a query to populate dashboard signals.";

  if (request && first(params.q).trim()) {
    try {
      const cookieHeader = (await cookies()).toString();
      initialResult = await searchServer(request, cookieHeader);
      initialStatus = `Search complete. ${initialResult.data.results.length} results.`;
    } catch (error) {
      initialStatus = `Search failed: ${(error as Error).message}`;
    }
  }

  return <DashboardClient initialForm={form} initialResult={initialResult} initialStatus={initialStatus} />;
}
