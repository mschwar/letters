"use client";

import { FormEvent, useState } from "react";

import { ResultPanels } from "../../components/result-panels";
import { useSearchStore } from "../../components/search-store";
import { login, search, type SearchResponse } from "../../lib/api";

export default function DashboardPage() {
  const [email, setEmail] = useState("owner@local.test");
  const [password, setPassword] = useState("ChangeMeNow!");
  const [authStatus, setAuthStatus] = useState("Not authenticated.");
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("guidance regarding family life and marriage");
  const [sourceName, setSourceName] = useState("");
  const [tag, setTag] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [limit, setLimit] = useState(5);
  const [sortBy, setSortBy] = useState<"relevance" | "date_desc" | "date_asc">("relevance");
  const [searchStatus, setSearchStatus] = useState("Run a query to populate dashboard signals.");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const { push } = useSearchStore();

  async function onLogin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setAuthStatus("Signing in...");
    try {
      await login(email.trim(), password);
      setAuthStatus("Authenticated. Session cookie active.");
    } catch (error) {
      setAuthStatus(`Auth failed: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function onSearch(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) {
      setSearchStatus("Query is required.");
      return;
    }

    setBusy(true);
    setSearchStatus("Searching...");
    try {
      const response = await search({
        query: query.trim(),
        limit,
        source_name: sourceName.trim() || undefined,
        tag: tag.trim() || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        sort_by: sortBy
      });
      setResult(response);
      setSearchStatus(`Search complete. ${response.data.results.length} results.`);
      push({ payload: response.data, meta: response.meta, query: query.trim(), at: new Date().toISOString() });
    } catch (error) {
      setSearchStatus(`Search failed: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-grid">
      <section className="panel stack">
        <h2>Session</h2>
        <form className="stack" onSubmit={onLogin}>
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <button disabled={busy} type="submit">Sign In</button>
        </form>
        <p className="status">{authStatus}</p>
      </section>

      <section className="panel stack">
        <h2>Retrieval</h2>
        <form className="stack" onSubmit={onSearch}>
          <label>
            Query
            <textarea rows={3} value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
          <label>
            Source
            <input value={sourceName} onChange={(e) => setSourceName(e.target.value)} placeholder="Universal House of Justice" />
          </label>
          <label>
            Tag
            <input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="funds" />
          </label>
          <div className="split-two">
            <label>
              Date from
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </label>
            <label>
              Date to
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </label>
          </div>
          <div className="split-two">
            <label>
              Limit
              <input
                type="number"
                min={1}
                max={20}
                value={limit}
                onChange={(e) => setLimit(Math.max(1, Math.min(20, Number(e.target.value) || 5)))}
              />
            </label>
            <label>
              Sort
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value as "relevance" | "date_desc" | "date_asc")}>
                <option value="relevance">Relevance</option>
                <option value="date_desc">Date newest</option>
                <option value="date_asc">Date oldest</option>
              </select>
            </label>
          </div>
          <button disabled={busy} type="submit">Run Search</button>
        </form>
        <p className="status">{searchStatus}</p>
      </section>

      {result ? <ResultPanels payload={result.data} meta={result.meta} /> : null}
    </div>
  );
}
