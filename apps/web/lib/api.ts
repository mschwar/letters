export type Confidence = { score: number; label: string };

export type SearchResult = {
  document_id: string;
  title: string;
  source_name: string;
  document_date: string;
  summary: string;
  snippet: string;
  score: number;
};

export type Citation = {
  ref: string;
  document_id: string;
  title: string;
  source_name: string;
  document_date: string;
  snippet: string;
  score: number;
};

export type SearchPayload = {
  query: string;
  answer: string;
  confidence: Confidence;
  citations: Citation[];
  results: SearchResult[];
};

export type SearchMeta = {
  retrieval_mode: string;
  sort_by?: string;
  result_counts?: { fts: number; vector: number };
};

export type SearchResponse = { data: SearchPayload; meta: SearchMeta };

export type SearchRequest = {
  query: string;
  limit: number;
  source_name?: string;
  tag?: string;
  date_from?: string;
  date_to?: string;
  sort_by: "relevance" | "date_desc" | "date_asc";
};

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api/v1";
}

async function asJson<T>(resp: Response): Promise<T> {
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const envelope = body as { error?: { message?: string }; detail?: string };
    const detail = envelope.error?.message ?? envelope.detail ?? `HTTP ${resp.status}`;
    throw new Error(detail);
  }
  return body as T;
}

export async function login(email: string, password: string): Promise<void> {
  const response = await fetch(`${apiBase()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password })
  });
  await asJson(response);
}

export async function search(request: SearchRequest): Promise<SearchResponse> {
  const response = await fetch(`${apiBase()}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request)
  });
  return asJson<SearchResponse>(response);
}

export async function searchServer(
  request: SearchRequest,
  cookieHeader: string
): Promise<SearchResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (cookieHeader) {
    headers.cookie = cookieHeader;
  }

  const response = await fetch(`${apiBase()}/search`, {
    method: "POST",
    headers,
    cache: "no-store",
    body: JSON.stringify(request)
  });
  return asJson<SearchResponse>(response);
}
