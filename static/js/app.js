/* ============================================================
   AI File Assistant — frontend logic
   Vanilla JS, no build step, no framework. Talks to the Flask
   API in app.py, which itself wraps the same core modules the
   MCP server uses.
   ============================================================ */

const API = {
  files: (folder = ".", recursive = true) =>
    fetch(`/api/files?folder=${encodeURIComponent(folder)}&recursive=${recursive}`).then(handle),
  stats: () => fetch("/api/stats").then(handle),
  health: () => fetch("/api/health").then(handle),
  read: (path) => fetch(`/api/read?path=${encodeURIComponent(path)}`).then(handle),
  search: (keyword, folder = ".") =>
    fetch(`/api/search?folder=${encodeURIComponent(folder)}&keyword=${encodeURIComponent(keyword)}`).then(handle),
  summarize: (path, style) =>
    fetch("/api/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, style }),
    }).then(handle),
  ask: (path, question) =>
    fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, question }),
    }).then(handle),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return fetch("/api/upload", { method: "POST", body: form }).then(handle);
  },
};

async function handle(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }
  return data;
}

// ---- File-type visual language -------------------------------------

const TYPE_META = {
  ".pdf": { label: "PDF", color: "#e15554" },
  ".docx": { label: "DOCX", color: "#5b8def" },
  ".xlsx": { label: "XLSX", color: "#3fa796" },
  ".xls": { label: "XLS", color: "#3fa796" },
  ".txt": { label: "TXT", color: "#e8a33d" },
};

function typeMeta(ext) {
  return TYPE_META[ext] || { label: (ext || "?").replace(".", "").toUpperCase() || "FILE", color: "#6b7280" };
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function highlight(text, term) {
  if (!term) return escapeHtml(text);
  const escaped = escapeHtml(text);
  const safeTerm = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return escaped.replace(new RegExp(`(${safeTerm})`, "gi"), "<mark>$1</mark>");
}

// ---- State -----------------------------------------------------------

let state = {
  files: [],
  activeFile: null,
  activeText: "",
  activeStyle: "concise",
  searchTerm: "",
};

// ---- Toasts -----------------------------------------------------------

function toast(message, type = "info") {
  const stack = document.getElementById("toastStack");
  const el = document.createElement("div");
  el.className = `toast${type === "error" ? " error" : ""}`;
  el.textContent = message;
  stack.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

// ---- Boot --------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  bindUpload();
  bindSearch();
  bindTabs();
  bindStyleChips();
  bindSummarize();
  bindAsk();
  document.getElementById("closeSearchBtn").addEventListener("click", showEmptyOrDoc);

  loadHealth();
  loadStats();
  loadCatalog();
});

// ---- Theme --------------------------------------------------------------

function initTheme() {
  const saved = localStorage.getItem("fa-theme") || "dark";
  document.body.dataset.theme = saved;
  syncThemeIcon(saved);
  document.getElementById("themeToggle").addEventListener("click", () => {
    const next = document.body.dataset.theme === "dark" ? "light" : "dark";
    document.body.dataset.theme = next;
    localStorage.setItem("fa-theme", next);
    syncThemeIcon(next);
  });
}

function syncThemeIcon(theme) {
  document.getElementById("iconMoon").style.display = theme === "dark" ? "block" : "none";
  document.getElementById("iconSun").style.display = theme === "light" ? "block" : "none";
}

// ---- Health / stats ribbon ------------------------------------------------

async function loadHealth() {
  try {
    const data = await API.health();
    const dot = document.getElementById("llmDot");
    const label = document.getElementById("llmLabel");
    if (data.llm_ready) {
      dot.className = "status-dot ready";
      label.textContent = `${data.llm_provider} connected`;
    } else {
      dot.className = "status-dot error";
      label.textContent = `${data.llm_provider} key missing`;
    }
  } catch (err) {
    document.getElementById("llmLabel").textContent = "backend unreachable";
  }
}

async function loadStats() {
  try {
    const data = await API.stats();
    document.querySelector("#statFiles .stat-value").textContent = data.supported_files;
    document.querySelector("#statSize .stat-value").textContent = formatBytes(data.total_size_bytes);
  } catch (err) {
    /* stats are non-critical, fail quietly */
  }
}

// ---- Catalog (sidebar file list) ------------------------------------------

async function loadCatalog() {
  try {
    const data = await API.files();
    state.files = data.files;
    renderCatalog(state.files);
  } catch (err) {
    toast(`Couldn't load files: ${err.message}`, "error");
  }
}

function renderCatalog(files) {
  const el = document.getElementById("catalog");
  document.getElementById("catalogCount").textContent = files.length;

  if (!files.length) {
    el.innerHTML = `<div class="catalog-empty">No files yet — drop one above to get started.</div>`;
    return;
  }

  el.innerHTML = files
    .map((f) => {
      const meta = typeMeta(f.extension);
      const activeClass = state.activeFile && state.activeFile.path === f.path ? " active" : "";
      const supportedClass = f.is_supported ? "" : " unsupported";
      return `
        <div class="file-card${activeClass}${supportedClass}" style="--tab-color:${meta.color}" data-path="${escapeHtml(f.path)}">
          <span class="file-card-icon">${meta.label}</span>
          <div class="file-card-body">
            <span class="file-card-name">${escapeHtml(f.name)}</span>
            <span class="file-card-meta">${formatBytes(f.size_bytes)} · ${f.modified.replace("T", " ")}</span>
          </div>
        </div>`;
    })
    .join("");

  el.querySelectorAll(".file-card:not(.unsupported)").forEach((card) => {
    card.addEventListener("click", () => openFile(card.dataset.path));
  });
}

// ---- Upload --------------------------------------------------------------

function bindUpload() {
  const dropzone = document.getElementById("dropzone");
  const input = document.getElementById("fileInput");

  document.getElementById("browseBtn").addEventListener("click", (e) => {
    e.stopPropagation();
    input.click();
  });
  dropzone.addEventListener("click", () => input.click());

  input.addEventListener("change", () => {
    if (input.files[0]) handleUpload(input.files[0]);
    input.value = "";
  });

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  });
}

async function handleUpload(file) {
  try {
    await API.upload(file);
    toast(`Uploaded ${file.name}`);
    await loadCatalog();
    await loadStats();
  } catch (err) {
    toast(`Upload failed: ${err.message}`, "error");
  }
}

// ---- Search -----------------------------------------------------------

function bindSearch() {
  const input = document.getElementById("searchInput");
  let debounceTimer;
  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const term = input.value.trim();
    debounceTimer = setTimeout(() => {
      if (term.length >= 2) runSearch(term);
      else if (term.length === 0) showEmptyOrDoc();
    }, 350);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && input.value.trim()) runSearch(input.value.trim());
  });
}

async function runSearch(term) {
  state.searchTerm = term;
  try {
    const data = await API.search(term);
    renderSearchResults(term, data.results);
  } catch (err) {
    toast(`Search failed: ${err.message}`, "error");
  }
}

function renderSearchResults(term, results) {
  document.getElementById("emptyState").hidden = true;
  document.getElementById("docWorkspace").hidden = true;
  const view = document.getElementById("searchResultsView");
  view.hidden = false;
  document.getElementById("searchTermLabel").textContent = `"${term}"`;

  const list = document.getElementById("resultsList");
  if (!results.length) {
    list.innerHTML = `<div class="catalog-empty">No matches for "${escapeHtml(term)}".</div>`;
    return;
  }

  list.innerHTML = results
    .map((r) => {
      const snippet = r.snippets[0] || "";
      return `
        <div class="result-item" data-path="${escapeHtml(r.file)}">
          <div class="result-item-header">
            <span>${escapeHtml(r.file)}</span>
            <span class="match-badge">${r.match_count} match${r.match_count === 1 ? "" : "es"}</span>
          </div>
          <p class="result-snippet">${highlight(snippet, term)}</p>
        </div>`;
    })
    .join("");

  list.querySelectorAll(".result-item").forEach((item) => {
    item.addEventListener("click", () => {
      document.getElementById("searchInput").value = "";
      openFile(item.dataset.path, term);
    });
  });
}

function showEmptyOrDoc() {
  document.getElementById("searchResultsView").hidden = true;
  if (state.activeFile) {
    document.getElementById("docWorkspace").hidden = false;
  } else {
    document.getElementById("emptyState").hidden = false;
  }
}

// ---- Opening a document ------------------------------------------------

async function openFile(path, highlightTerm = "") {
  const file = state.files.find((f) => f.path === path) || { path, name: path.split("/").pop(), extension: "" };
  state.activeFile = file;

  document.getElementById("emptyState").hidden = true;
  document.getElementById("searchResultsView").hidden = true;
  document.getElementById("docWorkspace").hidden = false;

  const meta = typeMeta(file.extension);
  document.getElementById("docSwatch").style.setProperty("--tab-color", meta.color);
  document.getElementById("docName").textContent = file.name;
  document.getElementById("docMeta").textContent = file.size_bytes ? `${formatBytes(file.size_bytes)} · ${file.path}` : file.path;

  document.getElementById("docPreview").textContent = "Loading…";
  resetSummaryPanel();
  resetChat();
  renderCatalog(state.files);

  try {
    const data = await API.read(path);
    state.activeText = data.text;
    const previewEl = document.getElementById("docPreview");
    previewEl.innerHTML = highlightTerm ? highlight(data.text, highlightTerm) : escapeHtml(data.text);
    switchTab("preview");
  } catch (err) {
    document.getElementById("docPreview").textContent = `Couldn't read this file: ${err.message}`;
    toast(err.message, "error");
  }
}

// ---- Tabs -----------------------------------------------------------

function bindTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === tab));
}

// ---- Summarize -----------------------------------------------------------

function bindStyleChips() {
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      state.activeStyle = chip.dataset.style;
    });
  });
}

function resetSummaryPanel() {
  document.getElementById("summaryResult").hidden = true;
  document.getElementById("summarizeHint").hidden = false;
  document.getElementById("summarizeHint").textContent = "Choose a style above and generate a summary of this document.";
  document.getElementById("summarizeScanFrame").classList.remove("scanning");
}

function bindSummarize() {
  document.getElementById("summarizeBtn").addEventListener("click", async () => {
    if (!state.activeFile) return;
    const btn = document.getElementById("summarizeBtn");
    const frame = document.getElementById("summarizeScanFrame");
    const hint = document.getElementById("summarizeHint");
    const resultCard = document.getElementById("summaryResult");

    btn.disabled = true;
    frame.classList.add("scanning");
    resultCard.hidden = true;
    hint.hidden = false;
    hint.textContent = "Reading the document and generating a summary…";

    try {
      const data = await API.summarize(state.activeFile.path, state.activeStyle);
      hint.hidden = true;
      resultCard.hidden = false;
      document.getElementById("summaryText").textContent = data.summary;
      document.getElementById("summaryFootnote").textContent = `Built from ${data.chunk_count || 1} chunk${data.chunk_count === 1 ? "" : "s"} · ${state.activeStyle} style`;
    } catch (err) {
      hint.hidden = false;
      hint.textContent = `Couldn't generate a summary: ${err.message}`;
      toast(err.message, "error");
    } finally {
      btn.disabled = false;
      frame.classList.remove("scanning");
    }
  });

  document.getElementById("copySummaryBtn").addEventListener("click", () => {
    const text = document.getElementById("summaryText").textContent;
    navigator.clipboard.writeText(text).then(() => toast("Summary copied"));
  });
}

// ---- Ask -----------------------------------------------------------

function resetChat() {
  document.getElementById("chatThread").innerHTML =
    '<p class="hint-text">Ask anything grounded in this document — answers are pulled from its most relevant sections only.</p>';
}

function bindAsk() {
  document.getElementById("askForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.activeFile) return;
    const input = document.getElementById("askInput");
    const question = input.value.trim();
    if (!question) return;

    const thread = document.getElementById("chatThread");
    const hint = thread.querySelector(".hint-text");
    if (hint) hint.remove();

    const qBubble = document.createElement("div");
    qBubble.className = "chat-bubble question";
    qBubble.textContent = question;
    thread.appendChild(qBubble);

    const loadingBubble = document.createElement("div");
    loadingBubble.className = "chat-bubble loading";
    loadingBubble.textContent = "Reading relevant sections…";
    thread.appendChild(loadingBubble);
    thread.scrollTop = thread.scrollHeight;

    input.value = "";
    document.getElementById("askBtn").disabled = true;

    try {
      const data = await API.ask(state.activeFile.path, question);
      loadingBubble.remove();
      const aBubble = document.createElement("div");
      aBubble.className = "chat-bubble answer";
      aBubble.textContent = data.answer;
      thread.appendChild(aBubble);
    } catch (err) {
      loadingBubble.remove();
      const aBubble = document.createElement("div");
      aBubble.className = "chat-bubble answer";
      aBubble.textContent = `Couldn't answer that: ${err.message}`;
      thread.appendChild(aBubble);
      toast(err.message, "error");
    } finally {
      document.getElementById("askBtn").disabled = false;
      thread.scrollTop = thread.scrollHeight;
    }
  });
}
