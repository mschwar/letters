import type { SearchPayload, SearchMeta } from "../lib/api";

export function ResultPanels({ payload, meta }: { payload: SearchPayload; meta: SearchMeta }) {
  return (
    <section className="panel stack">
      <h2>Answer</h2>
      <p>{payload.answer}</p>
      <div className="chip-row">
        <span className={`chip ${payload.confidence.label}`}>
          confidence {payload.confidence.label} ({payload.confidence.score})
        </span>
        <span className="chip">mode {meta.retrieval_mode}</span>
        <span className="chip">sort {meta.sort_by ?? "relevance"}</span>
      </div>
      <h3>Citations</h3>
      <ol className="stack-tight">
        {payload.citations.map((citation) => (
          <li key={citation.ref + citation.document_id}>
            {citation.ref} {citation.title || "(untitled)"} ({citation.document_date || "n/a"})
          </li>
        ))}
      </ol>
      <h3>Ranked Results</h3>
      <div className="card-grid">
        {payload.results.map((row) => (
          <article key={row.document_id} className="card">
            <h4>{row.title || "(untitled)"}</h4>
            <p className="meta">
              {row.source_name || "unknown source"} | {row.document_date || "n/a"} | score {row.score.toFixed(3)}
            </p>
            <p>{row.snippet || row.summary || "No preview."}</p>
            <p className="mono">{row.document_id}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
