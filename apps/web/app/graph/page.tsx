"use client";

import { useMemo } from "react";

import { useSearchStore } from "../../components/search-store";

type GraphNode = { id: string; label: string; kind: "query" | "citation" | "result"; x: number; y: number };
type GraphEdge = { id: string; from: string; to: string };

export default function GraphPage() {
  const { latest } = useSearchStore();

  const graph = useMemo(() => {
    if (!latest) return null;

    const citations = latest.payload.citations.slice(0, 6);
    const results = latest.payload.results.slice(0, 6);

    const nodes: GraphNode[] = [{ id: "query", label: latest.query, kind: "query", x: 460, y: 80 }];
    const edges: GraphEdge[] = [];

    citations.forEach((c, i) => {
      const id = `citation-${c.document_id}-${i}`;
      nodes.push({
        id,
        label: c.title || c.document_id,
        kind: "citation",
        x: 180 + i * 120,
        y: 220
      });
      edges.push({ id: `qc-${i}`, from: "query", to: id });
    });

    results.forEach((r, i) => {
      const id = `result-${r.document_id}-${i}`;
      nodes.push({
        id,
        label: r.title || r.document_id,
        kind: "result",
        x: 180 + i * 120,
        y: 380
      });
      edges.push({ id: `qr-${i}`, from: "query", to: id });
      const matchIndex = citations.findIndex((c) => c.document_id === r.document_id);
      if (matchIndex >= 0) {
        edges.push({
          id: `cr-${i}`,
          from: `citation-${citations[matchIndex].document_id}-${matchIndex}`,
          to: id
        });
      }
    });

    return { nodes, edges };
  }, [latest]);

  if (!graph) {
    return (
      <section className="panel stack">
        <h2>Relationship Graph</h2>
        <p>Run a search on Dashboard to populate graph data.</p>
      </section>
    );
  }

  const byId = new Map(graph.nodes.map((n) => [n.id, n]));

  return (
    <section className="panel stack">
      <h2>Relationship Graph</h2>
      <p className="status">
        Query to citation and ranked-result links for quick provenance scanning.
      </p>
      <svg viewBox="0 0 980 470" role="img" aria-label="Query relationship graph" className="graph">
        {graph.edges.map((edge) => {
          const from = byId.get(edge.from);
          const to = byId.get(edge.to);
          if (!from || !to) return null;
          return <line key={edge.id} x1={from.x} y1={from.y} x2={to.x} y2={to.y} className="graph-edge" />;
        })}
        {graph.nodes.map((node) => (
          <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
            <circle className={`graph-node ${node.kind}`} r={28} />
            <text textAnchor="middle" y={52} className="graph-label">
              {node.label.length > 28 ? `${node.label.slice(0, 28)}...` : node.label}
            </text>
          </g>
        ))}
      </svg>
    </section>
  );
}
