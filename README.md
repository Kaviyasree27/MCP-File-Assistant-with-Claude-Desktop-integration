# AI File Assistant

A document intelligence system that enables AI agents and users to **read, search, summarize, and answer questions** over local PDF, DOCX, XLSX, and TXT documents.

The project exposes the same core engine through:

- **MCP Server** for Claude Desktop and other MCP-compatible clients
- **Flask Web Application** for browser-based interaction

---

## Features

- Read PDF, DOCX, XLSX and TXT documents
- Search keywords across multiple documents
- AI-powered document summarization
- Retrieval-Augmented Document Q&A
- Upload and manage files
- Delete individual or all documents
- Secure file access with path validation
- Claude Desktop MCP integration

---

## Tech Stack

| Category | Technologies |
|----------|--------------|
| Backend | Python, Flask |
| MCP | Model Context Protocol (MCP) |
| AI | Groq Llama / Ollama |
| Document Parsing | PyMuPDF, python-docx, pandas, openpyxl |
| Frontend | HTML, CSS, JavaScript |
| Testing | Pytest |

---

## Architecture

```text
                 Claude Desktop
                       │
                       ▼
                 MCP Server
                       │
        ┌──────────────┴──────────────┐
        │                             │
   Shared Core Engine            Flask Web App
        │
 ├── File Readers
 ├── Search Engine
 ├── Document Processor
 └── LLM Client
```
## 📸 Screenshots

### 🖥️ User Interface

Modern web interface for uploading, browsing, and managing supported documents.

<img width="1600" height="884" alt="image" src="https://github.com/user-attachments/assets/1b59456b-2224-430a-8f61-52e47a47d1e7" />

---
### 🔗 MCP Server Connected

Claude Desktop successfully connected to the local MCP File Assistant server.

<img width="1600" height="1135" alt="image" src="https://github.com/user-attachments/assets/181a46ee-2609-486e-8e10-c78f686f3a01" />

---

### 📄 Read Document

Read PDF, DOCX, XLSX, and TXT documents directly through Claude Desktop using MCP.

<img width="1600" height="935" alt="image" src="https://github.com/user-attachments/assets/6c638b40-4417-4385-989f-2d1485b07ad3" />
<img width="1600" height="936" alt="image" src="https://github.com/user-attachments/assets/adf11f2e-5bba-4b0b-b0f6-3e75a5458552" />



---

### 📝 AI Document Summarization

Generate concise AI-powered summaries of lengthy documents using Groq Llama.

<img width="1600" height="920" alt="image" src="https://github.com/user-attachments/assets/a973326b-e272-4d58-b116-c769aeb66af4" />

---

### 🔍 Keyword Search

Search keywords across every indexed document with ranked search results.

<img width="1600" height="940" alt="image" src="https://github.com/user-attachments/assets/a6b0323c-4352-46af-95ca-24fd5fa474c6" />


---

### ❓ Document Question Answering

Ask natural language questions grounded in document contents using Retrieval-Augmented Generation (RAG).

<img width="1600" height="591" alt="image" src="https://github.com/user-attachments/assets/37fb0755-a70c-4785-b519-5e5c1cc4f8d7" />


---

### 🗑️ File Management

Delete individual files or remove all uploaded documents directly from the application.

<img width="1600" height="897" alt="image" src="https://github.com/user-attachments/assets/91548827-f15e-4142-acc0-2ce10f99c229" />


---

###  Claude Desktop MCP Integration

Claude Desktop successfully invokes custom MCP tools including Read, Search, Summarize, and Ask Document.

<img width="1600" height="941" alt="image" src="https://github.com/user-attachments/assets/07e29083-a482-4d10-bc97-a623a285a717" />


---

## 📁 Project Structure

```text
mcp-file-assistant/
│
├── app.py
├── server.py
├── config.py
├── file_readers.py
├── search_engine.py
├── document_processor.py
├── llm_client.py
├── templates/
├── static/
├── tests/
├── sample_documents/
├── requirements.txt
└── README.md
```

---

## 🚀 Installation

```bash
git clone <repository-url>

cd mcp-file-assistant

pip install -r requirements.txt

python app.py
```

Open:

```
http://127.0.0.1:5000
```

To start the MCP server:

```bash
python server.py
```

Configure Claude Desktop with the provided MCP configuration and restart the application.

---

## 🔧 MCP Tools

- Read Document
- Search Documents
- Summarize Document
- Ask Document
- List Files
- Delete File
- Delete All Files
---
