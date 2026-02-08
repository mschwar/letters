const loginForm = document.querySelector("#login-form");
const searchForm = document.querySelector("#search-form");
const searchBtn = document.querySelector("#search-btn");

const sessionStatus = document.querySelector("#session-status");
const searchStatus = document.querySelector("#search-status");

const resultPanel = document.querySelector("#result-panel");
const answer = document.querySelector("#answer");
const confidenceChip = document.querySelector("#confidence-chip");
const modeChip = document.querySelector("#mode-chip");
const citationsList = document.querySelector("#citations");
const resultsContainer = document.querySelector("#results");

let apiBase = "";

function setStatus(el, message, className = "status") {
  el.className = className;
  el.textContent = message;
}

function endpoint(path) {
  return `${apiBase}${path}`;
}

async function asJson(resp) {
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = body?.detail ?? body?.error?.message ?? `HTTP ${resp.status}`;
    throw new Error(detail);
  }
  return body;
}

function renderResults(payload) {
  resultPanel.hidden = false;
  answer.textContent = payload.answer || "No answer.";

  const conf = payload.confidence || { label: "low", score: 0 };
  confidenceChip.textContent = `confidence: ${conf.label} (${conf.score})`;
  confidenceChip.className = `chip ${conf.label}`;

  const mode = payload.meta?.retrieval_mode || "fts";
  modeChip.textContent = `mode: ${mode}`;

  citationsList.innerHTML = "";
  for (const c of payload.citations || []) {
    const item = document.createElement("li");
    item.textContent = `${c.ref} ${c.title || "(untitled)"} (${c.document_date || "n/a"})`;
    citationsList.appendChild(item);
  }

  resultsContainer.innerHTML = "";
  for (const r of payload.results || []) {
    const card = document.createElement("article");
    card.className = "card";
    const title = r.title || "(untitled)";
    const meta = `${r.source_name || "unknown source"} • ${r.document_date || "n/a"} • score ${Number(
      r.score || 0
    ).toFixed(3)}`;
    card.innerHTML = `
      <h4>${title}</h4>
      <p class="card-meta">${meta}</p>
      <p>${r.snippet || r.summary || ""}</p>
      <p class="card-meta">document_id: ${r.document_id}</p>
    `;
    resultsContainer.appendChild(card);
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const base = document.querySelector("#api-base").value.trim().replace(/\/+$/, "");
  const email = document.querySelector("#email").value.trim();
  const password = document.querySelector("#password").value;

  apiBase = base;
  setStatus(sessionStatus, "Signing in...", "status");

  try {
    await asJson(
      await fetch(endpoint("/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      })
    );
    searchBtn.disabled = false;
    setStatus(sessionStatus, "Authenticated. Session cookie set.", "status high");
    setStatus(searchStatus, "Ready. Enter a natural-language query.", "status muted");
  } catch (err) {
    searchBtn.disabled = true;
    setStatus(sessionStatus, `Auth failed: ${err.message}`, "status low");
  }
});

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!apiBase) {
    setStatus(searchStatus, "Set API base URL and sign in first.", "status low");
    return;
  }

  const query = document.querySelector("#query").value.trim();
  const limit = Number(document.querySelector("#limit").value || 5);
  const sourceName = document.querySelector("#source-name").value.trim();
  const tag = document.querySelector("#tag").value.trim();
  const dateFrom = document.querySelector("#date-from").value;
  const dateTo = document.querySelector("#date-to").value;
  const sortBy = document.querySelector("#sort-by").value;

  if (!query) {
    setStatus(searchStatus, "Query is required.", "status low");
    return;
  }

  setStatus(searchStatus, "Searching...", "status");
  try {
    const payload = { query, limit, sort_by: sortBy };
    if (sourceName) payload.source_name = sourceName;
    if (tag) payload.tag = tag;
    if (dateFrom) payload.date_from = dateFrom;
    if (dateTo) payload.date_to = dateTo;

    const body = await asJson(
      await fetch(endpoint("/search"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      })
    );
    renderResults({ ...body.data, meta: body.meta || {} });
    setStatus(searchStatus, "Search complete.", "status high");
  } catch (err) {
    setStatus(searchStatus, `Search failed: ${err.message}`, "status low");
  }
});
