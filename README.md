# AI File Assistant

A document-intelligence engine — read, search, summarize, and answer questions about local PDF/DOCX/XLSX/TXT files — exposed through **two interfaces built on the same tested core**:

1. **An MCP server** (`server.py`) for AI agents — Claude Desktop, Claude Code, or any MCP-compatible client can call it as a tool.
2. **A web app** (`app.py` + browser UI) for humans — a drag-and-drop file browser, keyword search, LLM summarization, and a document Q&A chat, all in the browser.

Both interfaces are thin adapters over the same four core modules (`file_readers.py`, `search_engine.py`, `document_processor.py`, `llm_client.py`), so there's exactly one implementation of "how to read a PDF" or "how to rank chunks for a question" — not two copies that can drift apart. That separation is the main engineering idea of this project.

Built to demonstrate practical software engineering around an LLM integration, not just a wrapper around an API call: module separation, input validation and path-traversal protection, a swappable LLM backend, retrieval-augmented Q&A without a vector database, and a real test suite (36 tests, both interfaces covered).

## What it looks like

The web UI's visual language is a digitized library card catalog: each file gets a colored index tab by type (PDF/DOCX/XLSX/TXT), and a thin scanline sweeps across the preview while a document is being read by the model — a detail that ties the loading state to what's actually happening, rather than a generic spinner.

Run `python app.py` and open `http://localhost:5000` to see it live.

## Why MCP

The Model Context Protocol is the standard Anthropic and others are converging on for connecting AI models to external tools and data sources. Rather than hardcoding document logic into a single chatbot, this project exposes document operations as **MCP tools** — discrete, typed, independently callable functions that any MCP client can use. That means the same server works with Claude Desktop today and with a different agent framework tomorrow, with zero code changes.

## Features

**Core engine (shared by both interfaces):**
- **Multi-format reading** — PDF (PyMuPDF), Word (`python-docx`), Excel (`pandas` + `openpyxl`), and plain text, all normalized to plain text through one interface.
- **Folder browsing** — list files in a directory, recursively or not, with metadata (size, modified time, supported/unsupported flag).
- **Keyword search** — search every supported document in a folder, ranked by match count, with context snippets around each hit.
- **LLM summarization** — map-reduce summarization so long documents don't blow past context limits: each chunk is summarized independently, then the partial summaries are combined into one final summary.
- **Document Q&A (RAG-lite)** — answers are grounded in the most relevant sections of a document, not the whole thing dumped into the prompt. Relevance ranking is a small dependency-free scoring function (see [Design Decisions](#design-decisions)).
- **Pluggable LLM backend** — switch between Groq's free-tier hosted API and a fully local Ollama model with one environment variable. No paid API is required to run this project.
- **Path-traversal protection** — every file path passed to a tool is resolved and validated against a configured base directory before any I/O happens.

**Web UI (`app.py`):**
- Drag-and-drop file upload, with server-side file-type validation
- Live catalog sidebar with per-type color coding and file metadata
- Debounced full-text search across every file, with highlighted match snippets
- One-click summarization with three styles (concise / detailed / bullet points)
- A chat-style Q&A panel per document, grounded in that document's content
- A status badge reporting whether the LLM backend is actually reachable, not just configured
- Light/dark theme toggle, responsive layout down to mobile, visible keyboard focus, respects reduced-motion preference

**MCP server (`server.py`):**
- Same 5 operations (`list_files`, `read_document`, `search_documents`, `summarize`, `ask_document`) exposed as MCP tools for Claude Desktop / Claude Code / any MCP client

## Tech Stack

| Layer | Choice |
|---|---|
| Protocol | MCP Python SDK (`mcp`, `FastMCP`) |
| Web backend | Flask |
| Frontend | Vanilla HTML / CSS / JS — no build step, no framework |
| PDF parsing | PyMuPDF (`fitz`) |
| Word parsing | `python-docx` |
| Excel parsing | `pandas` + `openpyxl` |
| LLM inference | Groq (free tier) or Ollama (local), pluggable |
| Tests | `pytest` (36 tests: core engine + web API) |

## Project Structure

```
mcp-file-assistant/
├── server.py                 # MCP server entrypoint — registers all tools
├── app.py                    # Flask web app — REST API + serves the UI
├── templates/
│   └── index.html            # Single-page web UI shell
├── static/
│   ├── css/style.css         # Design system (card-catalog theme, light/dark)
│   └── js/app.js             # Frontend logic — no framework, no build step
├── config.py                 # Centralized env-driven configuration
├── file_readers.py           # PDF/DOCX/XLSX/TXT parsing + path safety
├── search_engine.py          # Keyword search across a folder
├── document_processor.py     # Chunking, summarization, RAG-style Q&A
├── llm_client.py             # Groq / Ollama backend abstraction
├── tests/                    # pytest suite (36 tests: engine + web API)
├── sample_documents/         # Demo files so it works out of the box
├── requirements.txt
├── .env.example
├── claude_desktop_config.example.json
└── README.md
```

**Why this split:** `server.py` and `app.py` are both thin adapters — one for AI agents, one for a browser — but neither contains business logic. `file_readers.py` only knows about turning bytes into text. `document_processor.py` only knows about chunking/summarizing/answering. `llm_client.py` only knows about talking to a model API. Each module is independently unit-testable and none of them import `mcp` or `flask` — meaning the core logic could power a CLI or a different protocol tomorrow without changes.

## Setup (Windows / macOS / Linux)

**1. Clone and create a virtual environment**

```bash
git clone <your-repo-url>
cd mcp-file-assistant
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

**2. Configure environment variables**

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Then edit `.env`:
- For the free hosted option: get a key at [console.groq.com/keys](https://console.groq.com/keys) and set `GROQ_API_KEY`.
- For a fully offline, zero-key option: install [Ollama](https://ollama.com), run `ollama pull llama3.2`, set `MCP_LLM_PROVIDER=ollama`.

By default `MCP_FILES_BASE_DIR` points at the bundled `sample_documents/` folder so you can try it immediately.

**3. Run the test suite**

```bash
pytest tests/ -v
```

**4. Run the web app** (the easiest way to try everything, and the best thing to demo live)

```bash
python app.py
```

Open **http://localhost:5000** in your browser. The bundled `sample_documents/` folder is loaded by default so there's something to click on immediately.

**5. Run the MCP server standalone** (stdio transport, used by Claude Desktop)

```bash
python server.py
```

## Connecting to Claude Desktop

Add the server to your Claude Desktop MCP config (`claude_desktop_config.json`, found via Settings → Developer → Edit Config). A template is provided in `claude_desktop_config.example.json`:

```json
{
  "mcpServers": {
    "file-assistant": {
      "command": "python",
      "args": ["C:\\path\\to\\mcp-file-assistant\\server.py"],
      "env": {
        "MCP_FILES_BASE_DIR": "C:\\path\\to\\your\\documents",
        "GROQ_API_KEY": "your_groq_api_key_here"
      }
    }
  }
}
```

Restart Claude Desktop and the five tools below become available in conversation.

## MCP Tools Exposed

| Tool | Description |
|---|---|
| `list_files(folder_path, recursive)` | List files with metadata under a folder |
| `read_document(file_path)` | Extract plain text from a PDF/DOCX/XLSX/TXT file |
| `search_documents(folder_path, keyword, recursive)` | Keyword search across a folder, ranked by match count |
| `summarize(file_path, style)` | LLM summary — `"concise"`, `"detailed"`, or `"bullets"` |
| `ask_document(file_path, question)` | RAG-style Q&A grounded in the most relevant document sections |

## Design Decisions

A few choices worth being able to speak to in an interview:

**Why no vector database for Q&A?** For a single-user local file assistant, standing up an embedding model plus a vector store (Chroma, FAISS, Pinecone) is real infrastructure for a problem that a few hundred documents don't need. Instead, `document_processor.py` chunks each document and scores chunks by query-term overlap and frequency — a transparent, dependency-free heuristic that's fast and good enough at this scale. The tradeoff is honest: it won't catch semantic matches with zero shared vocabulary (e.g. "profit" vs. "revenue"). The fix, if this became a multi-thousand-document product, would be swapping `rank_chunks_by_relevance` for embedding similarity — the rest of the pipeline (chunk → rank → prompt) doesn't change, which is the point of keeping that function isolated.

**Why a pluggable LLM backend instead of hardcoding one provider?** `llm_client.py` defines an `LLMClient` abstract base class with a single `generate()` method; `GroqClient` and `OllamaClient` both implement it, and `get_llm_client()` picks one based on config. This is a small Strategy pattern that pays for itself twice: it means the project genuinely runs for free (Groq's free tier or a fully local Ollama model — no card required), and it means adding a third provider is one new class, not a rewrite.

**Why map-reduce summarization instead of one big prompt?** Feeding an entire large document into a single prompt risks exceeding context limits and produces summaries that skew toward whatever was near the end of the prompt. Chunking, summarizing each chunk independently, then summarizing the summaries keeps every part of the document represented and scales to arbitrarily long files.

**Why the explicit path-sandboxing layer?** Any tool that takes a file path as a string from an LLM-driven caller is a path-traversal risk (`../../etc/passwd`-style attacks) if you don't validate it. `resolve_safe_path()` in `file_readers.py` resolves every incoming path against a configured `BASE_DIR` and rejects anything that escapes it, before any file is opened. It's a small function, but it's the difference between a demo and something that's actually safe to point at a real folder.

**Why two interfaces over one core?** It would be easy to build the web UI logic directly into `server.py`'s tool functions, or vice versa. Instead, `app.py` and `server.py` both import from the same four modules and contain zero business logic themselves — they only translate between "MCP tool call" or "HTTP request" and a plain Python function call. This is the same idea as an API layer sitting in front of a service layer: the moment you have two ways of triggering the same operation (a human clicking a button, an AI agent calling a tool), duplicating the logic behind each is where bugs start disagreeing with each other.

## Testing

```bash
pytest tests/ -v
```

36 tests covering:
- All four file format readers, including malformed/missing files
- Path-traversal rejection (via the core engine, and again via the web API to confirm it holds up through both interfaces)
- Recursive vs. non-recursive folder listing
- Keyword search correctness, case-insensitivity, and empty-result handling
- Chunking correctness (including overlap behavior) and relevance ranking
- Every Flask API endpoint: health, stats, list, read, search, upload (including rejecting unsupported file types), and input validation on summarize/ask

LLM calls (`summarize`, `ask_document`) are isolated behind `llm_client.py` and not exercised in the automated suite, since they require a live API key or a running Ollama instance — the retrieval and chunking logic they depend on is tested directly instead.

## Possible Extensions

- Swap the heuristic chunk ranker for embedding-based semantic search (e.g. `sentence-transformers` + FAISS) once document volume justifies it.
- Multi-document Q&A (answer a question by searching across an entire folder, not just one file).
- A minimal web UI (Flask) as a thin client over the same core modules.
- Streaming responses from the LLM for a more responsive summarize/ask experience.

## License

MIT — see [LICENSE](LICENSE).
