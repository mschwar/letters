"use client";

import { FormEvent, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { login, type SearchRequest, type SearchResponse } from "../lib/api";
import { ResultPanels } from "./result-panels";
import { useSearchStore } from "./search-store";

type DashboardFormState = {
  query: string;
  sourceName: string;
  tag: string;
  dateFrom: string;
  dateTo: string;
  limit: number;
  sortBy: SearchRequest["sort_by"];
};

type DashboardClientProps = {
  initialForm: DashboardFormState;
  initialResult: SearchResponse | null;
  initialStatus: string;
};

function toParams(form: DashboardFormState): string {
  const params = new URLSearchParams();
  params.set("q", form.query.trim());
  params.set("limit", String(form.limit));
  params.set("sort", form.sortBy);
  if (form.sourceName.trim()) params.set("source", form.sourceName.trim());
  if (form.tag.trim()) params.set("tag", form.tag.trim());
  if (form.dateFrom) params.set("from", form.dateFrom);
  if (form.dateTo) params.set("to", form.dateTo);
  return params.toString();
}

export function DashboardClient({ initialForm, initialResult, initialStatus }: DashboardClientProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authStatus, setAuthStatus] = useState("Not authenticated.");
  const [authBusy, setAuthBusy] = useState(false);
  const [searchStatus, setSearchStatus] = useState(initialStatus);
  const [pending, startTransition] = useTransition();
  const router = useRouter();
  const { push } = useSearchStore();

  const [form, setForm] = useState<DashboardFormState>(initialForm);

  useEffect(() => {
    setForm(initialForm);
    setSearchStatus(initialStatus);
  }, [initialForm, initialStatus]);

  useEffect(() => {
    if (!initialResult) return;
    push({
      payload: initialResult.data,
      meta: initialResult.meta,
      query: initialResult.data.query,
      at: new Date().toISOString()
    });
  }, [initialResult, push]);

  const searchBusy = pending;
  const hasResult = useMemo(() => Boolean(initialResult), [initialResult]);

  async function onLogin(event: FormEvent) {
    event.preventDefault();
    setAuthBusy(true);
    setAuthStatus("Signing in...");
    try {
      await login(email.trim(), password);
      setAuthStatus("Authenticated. Session cookie active.");
    } catch (error) {
      setAuthStatus(`Auth failed: ${(error as Error).message}`);
    } finally {
      setAuthBusy(false);
    }
  }

  function onSearch(event: FormEvent) {
    event.preventDefault();
    if (!form.query.trim()) {
      setSearchStatus("Query is required.");
      return;
    }
    const params = toParams(form);
    setSearchStatus("Searching...");
    startTransition(() => {
      router.push(`/dashboard?${params}`);
    });
  }

  return (
    <div className="page-grid">
      <section className="panel stack">
        <h2>Session</h2>
        <form className="stack" onSubmit={onLogin}>
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" />
          </label>
          <button disabled={authBusy || searchBusy} type="submit">Sign In</button>
        </form>
        <p className="status">{authStatus}</p>
      </section>

      <section className="panel stack">
        <h2>Retrieval</h2>
        <form className="stack" onSubmit={onSearch}>
          <label>
            Query
            <textarea
              rows={3}
              value={form.query}
              onChange={(e) => setForm((prev) => ({ ...prev, query: e.target.value }))}
            />
          </label>
          <label>
            Source
            <input
              value={form.sourceName}
              onChange={(e) => setForm((prev) => ({ ...prev, sourceName: e.target.value }))}
              placeholder="Universal House of Justice"
            />
          </label>
          <label>
            Tag
            <input
              value={form.tag}
              onChange={(e) => setForm((prev) => ({ ...prev, tag: e.target.value }))}
              placeholder="funds"
            />
          </label>
          <div className="split-two">
            <label>
              Date from
              <input
                type="date"
                value={form.dateFrom}
                onChange={(e) => setForm((prev) => ({ ...prev, dateFrom: e.target.value }))}
              />
            </label>
            <label>
              Date to
              <input
                type="date"
                value={form.dateTo}
                onChange={(e) => setForm((prev) => ({ ...prev, dateTo: e.target.value }))}
              />
            </label>
          </div>
          <div className="split-two">
            <label>
              Limit
              <input
                type="number"
                min={1}
                max={20}
                value={form.limit}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    limit: Math.max(1, Math.min(20, Number(e.target.value) || 5))
                  }))
                }
              />
            </label>
            <label>
              Sort
              <select
                value={form.sortBy}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, sortBy: e.target.value as SearchRequest["sort_by"] }))
                }
              >
                <option value="relevance">Relevance</option>
                <option value="date_desc">Date newest</option>
                <option value="date_asc">Date oldest</option>
              </select>
            </label>
          </div>
          <button disabled={searchBusy || authBusy} type="submit">Run Search</button>
        </form>
        <p className="status">{searchStatus}</p>
      </section>

      {hasResult && initialResult ? <ResultPanels payload={initialResult.data} meta={initialResult.meta} /> : null}
    </div>
  );
}
