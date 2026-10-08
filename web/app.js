"use strict";

const state = {
  token: "",
  searchOnly: true,
  users: [],
  totalChunks: 0,
  currentUser: null,
};

const SUGGESTIONS = [
  "What is the Q3 infrastructure budget?",
  "What is the Atlas migration rollback plan?",
  "What is the L4 engineer salary band?",
  "What caused the June payments outage?",
  "How many paid time off days do we get?",
  "What is the Project Hawk offer range?",
];

const el = (id) => document.getElementById(id);

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function toast(message) {
  const t = el("toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => (t.hidden = true), 4000);
}

function groupChip(group) {
  const label = group.replace(/^group:/, "");
  const cls = group === "group:admin" ? "chip chip-admin" : "chip chip-group";
  return `<span class="${cls}">${escapeHtml(label)}</span>`;
}

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${state.token}` },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(120000),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(typeof detail.detail === "string" ? detail.detail : `Request failed (${res.status}); check the input and retry.`);
  }
  return res.json();
}

/* ---------- Bootstrap ---------- */

async function checkHealth() {
  const pill = el("health-pill");
  try {
    const res = await fetch("/health", {signal: AbortSignal.timeout(10000)});
    if (!res.ok) throw new Error();
    const health = await res.json();
    state.searchOnly = health.search_only !== false;
    el("ask-btn").disabled = state.searchOnly;
    el("suggestions").hidden = state.searchOnly;
    el("ask-input").disabled = state.searchOnly;
    el("ask-empty").querySelector("p").textContent = state.searchOnly
      ? "Search-only mode: generated answers are disabled. Open Search evidence."
      : "Generated answers are untrusted drafts. Verify each claim against the source excerpts.";
    el("search-mode").innerHTML = (health.retrieval_modes || ["bm25"]).map(mode =>
      `<option value="${escapeHtml(mode)}">${escapeHtml(MODE_LABELS[mode] || mode)}</option>`).join("");
    pill.textContent = state.searchOnly ? "search only" : "API online (model not checked)";
    pill.className = "stat-pill ok";
  } catch {
    pill.textContent = "offline";
    pill.className = "stat-pill down";
  }
}

async function loadUsers() {
  const res = await fetch("/api/users", {signal: AbortSignal.timeout(10000), headers: {Authorization: `Bearer ${state.token}`}});
  if (!res.ok) throw new Error("Demo token was not accepted");
  const data = await res.json();
  state.users = data.users;
  state.totalChunks = data.users[0].visible_chunks;
  el("corpus-stat").textContent = `${state.totalChunks} accessible chunks`;
  renderUsers();
  selectUser(state.users[0]);
}

function renderUsers() {
  const list = el("user-list");
  list.innerHTML = "";
  for (const user of state.users) {
    const card = document.createElement("button");
    card.className = "user-card";
    card.dataset.userId = user.user_id;
    card.innerHTML = `
      <div class="name">
        <span>${escapeHtml(user.name)}</span>
        <span class="visible">${user.visible_chunks} accessible chunks</span>
      </div>
      <div class="user-groups">${user.groups.map(groupChip).join("")}</div>`;
    card.addEventListener("click", () => selectUser(user));
    list.appendChild(card);
  }
}

function selectUser(user) {
  state.currentUser = user;
  document.querySelectorAll(".user-card").forEach((c) => {
    c.classList.toggle("is-active", c.dataset.userId === user.user_id);
  });
  el("ask-user-name").textContent = user.name;
  el("ask-user-visibility").textContent = `can see ${user.visible_chunks} chunks`;
}

/* ---------- Ask ---------- */

function renderSuggestions() {
  const box = el("suggestions");
  box.innerHTML = "";
  for (const q of SUGGESTIONS) {
    const b = document.createElement("button");
    b.className = "suggestion";
    b.type = "button";
    b.textContent = q;
    b.addEventListener("click", () => {
      el("ask-input").value = q;
      el("ask-form").requestSubmit();
    });
    box.appendChild(b);
  }
}

function renderAnswer(data) {
  el("ask-empty").hidden = true;
  el("ask-result").hidden = false;

  const withCitations = escapeHtml(data.answer).replace(
    /\[([A-Za-z0-9_-]+)\]/g,
    (_, id) => data.citations.includes(id) ? `<cite tabindex="0" role="button" data-doc="${id}">${id}</cite>` : `[${id}]`
  );
  el("answer-status").textContent = `Generated answer: ${data.trace?.answer_status || "untrusted draft"}`;
  el("answer-body").classList.toggle("review-required", data.trace?.answer_presentation?.status === "review_required");
  el("answer-body").innerHTML = withCitations || "<em>No answer produced.</em>";
  el("answer-latency").textContent = `${Math.round(data.latency_ms.total)} ms`;

  el("answer-citations").innerHTML = data.citations.length
    ? `<span class="muted">Cited sources:</span> ` +
      data.citations.map((c) => `<span class="chip chip-group">${escapeHtml(c)}</span>`).join("")
    : `<span class="muted">No sources cited.</span>`;

  el("evidence-count").textContent = `${data.evidence.length} authorized chunk(s)`;
  const list = el("evidence-list");
  list.innerHTML = "";
  if (!data.evidence.length) {
    list.innerHTML = `<p class="muted">No permitted evidence matched this question for this user.</p>`;
  }
  for (const ev of data.evidence) {
    const item = document.createElement("div");
    item.className = "evidence-item" + (ev.cited ? " cited" : "");
    item.dataset.doc = ev.doc_id;
    const acl = ev.allowed_principals.length
      ? ev.allowed_principals.map(groupChip).join("")
      : `<span class="chip chip-admin">admin only</span>`;
    item.innerHTML = `
      <div class="ev-head">
        <span class="ev-title">${escapeHtml(ev.title)}</span>
        <span class="ev-meta">
          <span class="chip chip-src">${escapeHtml(ev.source)}</span>
          <span class="chip chip-ghost mono">${escapeHtml(ev.doc_id)}</span>
          <span class="score-badge">${ev.score}</span>
          ${ev.cited ? '<span class="cited-badge">cited</span>' : ""}
        </span>
      </div>
      <div class="ev-meta">Chunk: ${escapeHtml(ev.chunk_id)}</div>
      <div class="ev-text">${escapeHtml(ev.text)}</div>
      <div class="ev-acl"><span class="lbl">visible to:</span> ${acl}</div>`;
    list.appendChild(item);
  }

  renderTrace(data.trace, data.latency_ms);
  wireCitationClicks();
}

function renderTrace(trace, latency) {
  const body = el("trace-body");
  const critic = trace.critic?.verdict || "not available";
  body.textContent = `Answer state: ${trace.answer_status || "draft"}. ` +
    `Verified evidence: ${trace.verified_chunks || 0} chunk(s). ` +
    `Omitted by evidence budget: ${trace.evidence_omitted || 0}. ` +
    `Planner fallback: ${Boolean(trace.planner_fallback)}. ` +
    `Assessment fallback: ${Boolean(trace.assessment_fallback)}. ` +
    `Synthesis unavailable: ${Boolean(trace.synthesis_fallback)}. ` +
    `Critic: ${critic} (source agreement only, never a safety verdict).`;

}

function wireCitationClicks() {
  document.querySelectorAll("cite[data-doc]").forEach((c) => {
    c.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); c.click(); } });
    c.addEventListener("click", () => {
      const target = document.querySelector(`.evidence-item[data-doc="${c.dataset.doc}"]`);
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "center" });
        target.style.transition = "outline 0.2s";
        target.style.outline = "2px solid var(--primary-strong)";
        setTimeout(() => (target.style.outline = "none"), 1200);
      }
    });
  });
}

async function onAsk(event) {
  event.preventDefault();
  const question = el("ask-input").value.trim();
  if (!question || !state.currentUser || state.searchOnly) return;
  const btn = el("ask-btn");
  btn.disabled = true;
  btn.textContent = "Thinking";
  el("ask-empty").hidden = true;
  el("ask-result").hidden = false;
  el("answer-body").classList.remove("review-required");
  el("answer-body").innerHTML = `<div class="loading"><span class="spinner"></span> Planning, retrieving, verifying, and synthesizing&hellip;</div>`;
  el("answer-status").textContent = "Generating untrusted draft";
  el("answer-latency").textContent = "";
  el("answer-citations").innerHTML = "";
  el("evidence-list").innerHTML = "";
  el("evidence-count").textContent = "";
  el("trace-body").innerHTML = "";
  try {
    const data = await api("/api/ask", {
      user_id: state.currentUser.user_id,
      question,
    });
    renderAnswer(data);
  } catch (err) {
    el("answer-status").textContent = "Answer unavailable";
    el("answer-body").textContent = `${err.message}. Use Search evidence to inspect permitted sources.`;
    toast(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Ask";
  }
}

/* ---------- Compare ---------- */

const MODE_LABELS = {
  bm25: "Keyword (BM25)",
  vector: "Semantic (vectors)",
  hybrid: "Hybrid (RRF fusion)",
  "hybrid+rerank": "Hybrid + reranker",
};

async function onCompare(event) {
  event.preventDefault();
  const query = el("compare-input").value.trim();
  if (!state.currentUser) { toast("Connect with the demo token before searching."); return; }
  if (!query) return;
  const btn = el("compare-btn");
  btn.disabled = true;
  btn.textContent = "Running";
  el("compare-grid").innerHTML = `<div class="loading"><span class="spinner"></span> Searching permitted evidence&hellip;</div>`;
  el("compare-visibility").hidden = true;
  try {
    const data = await api("/api/search", {
      user_id: state.currentUser.user_id,
      query,
      mode: el("search-mode").value,
    });
    renderCompare(data);
  } catch (err) {
    el("compare-grid").innerHTML = `<span style="color:var(--danger)">${escapeHtml(err.message)}</span>`;
    toast(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Search";
  }
}

function renderCompare(data) {
  const banner = el("compare-visibility");
  banner.hidden = false;
  banner.innerHTML = `As <strong>${escapeHtml(state.currentUser.name)}</strong>, search covers ${data.visible_chunks} authorized chunks.`;

  const grid = el("compare-grid");
  grid.innerHTML = "";
  for (const mode of Object.keys(data.modes)) {
    const md = data.modes[mode];
    const lat = md.latency_ms.total ? `${Math.round(md.latency_ms.total)} ms` : "";
    const card = document.createElement("div");
    card.className = "mode-card";
    const rows = md.error ? `<p class="muted">${escapeHtml(md.error)}</p>` : md.results.length
      ? md.results
          .map(
            (r, i) => `
        <div class="mode-result">
          <div class="mr-title">${i + 1}. ${escapeHtml(r.title)}</div>
          <div class="mr-meta">
            <span class="chip chip-src">${escapeHtml(r.source)}</span>
            <span class="mono">${escapeHtml(r.doc_id)} / ${escapeHtml(r.chunk_id)}</span>
            <span class="score-badge">${r.score}</span>
          </div>
          <details><summary>Read source excerpt (untrusted)</summary><p class="ev-text">${escapeHtml(r.text)}</p></details>
        </div>`
          )
          .join("")
      : `<p class="muted">No results.</p>`;
    card.innerHTML = `<h4>${MODE_LABELS[mode]}</h4><div class="mode-latency">${lat}</div>${rows}`;
    grid.appendChild(card);
  }
}

/* ---------- Tabs ---------- */

function wireTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => { t.classList.remove("is-active"); t.setAttribute("aria-selected", "false"); });
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("is-active"));
      tab.classList.add("is-active");
      tab.setAttribute("aria-selected", "true");
      document.querySelector(`.panel[data-panel="${tab.dataset.tab}"]`).classList.add("is-active");
    });
  });
}

/* ---------- Init ---------- */

async function init() {
  wireTabs();
  renderSuggestions();
  el("ask-form").addEventListener("submit", onAsk);
  el("compare-form").addEventListener("submit", onCompare);
  await checkHealth();
  el("connect-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    state.currentUser = null;
    state.users = [];
    renderUsers();
    el("ask-result").hidden = true;
    el("compare-grid").innerHTML = "";
    el("compare-visibility").hidden = true;
    el("corpus-stat").textContent = "Not connected";
    el("ask-user-name").textContent = "â€”";
    el("ask-user-visibility").textContent = "";
    state.token = el("demo-token").value;
    el("demo-token").value = "";
    try { await loadUsers(); toast("Connected to the configured demo identity"); }
    catch (err) { state.token = ""; state.currentUser = null; state.users = []; renderUsers(); toast(err.message); }
  });
}

init();
