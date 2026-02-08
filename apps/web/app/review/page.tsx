"use client";

import { useMemo } from "react";

import { useSearchStore } from "../../components/search-store";

function toDateLabel(raw: string): string {
  if (!raw) return "n/a";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toISOString().slice(0, 10);
}

export default function ReviewPage() {
  const { latest } = useSearchStore();

  const review = useMemo(() => {
    if (!latest) return null;
    const payload = latest.payload;
    const lowConfidence = payload.confidence.score < 0.6;
    const weakCitations = payload.citations.filter((c) => !c.document_date || !c.source_name);
    const shortSnippets = payload.results.filter((r) => {
      const text = (r.snippet || r.summary || "").trim();
      return text.length < 80;
    });
    return { lowConfidence, weakCitations, shortSnippets };
  }, [latest]);

  if (!latest || !review) {
    return (
      <section className="panel stack">
        <h2>Review Queue</h2>
        <p>Run a search from Dashboard to populate review checks.</p>
      </section>
    );
  }

  return (
    <div className="page-grid single">
      <section className="panel stack">
        <h2>Review Queue</h2>
        <p className="mono">Query: {latest.query}</p>
        <p className="status">Captured at {toDateLabel(latest.at)}</p>
        <div className="chip-row">
          <span className={`chip ${latest.payload.confidence.label}`}>
            confidence {latest.payload.confidence.label} ({latest.payload.confidence.score})
          </span>
          <span className="chip">{latest.meta.retrieval_mode}</span>
          <span className="chip">{latest.payload.citations.length} citations</span>
        </div>
      </section>

      <section className="panel stack">
        <h3>Checks</h3>
        <ul className="stack-tight">
          <li>{review.lowConfidence ? "Needs manual answer review." : "Confidence acceptable."}</li>
          <li>{review.weakCitations.length} citations missing source/date metadata.</li>
          <li>{review.shortSnippets.length} ranked results have short preview text (&lt;80 chars).</li>
        </ul>
      </section>

      <section className="panel stack">
        <h3>Citation Audit</h3>
        <ol className="stack-tight">
          {latest.payload.citations.map((citation) => (
            <li key={citation.ref + citation.document_id}>
              <p>
                {citation.ref} {citation.title || "(untitled)"}
              </p>
              <p className="meta">
                {citation.source_name || "unknown source"} | {citation.document_date || "n/a"} | score{" "}
                {citation.score.toFixed(3)}
              </p>
              <p>{citation.snippet || "No citation snippet."}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
