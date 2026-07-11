"""
Flask web application for the AI File Assistant.

This is a second interface on top of the exact same core engine used by
the MCP server (server.py): file_readers, search_engine, document_processor,
and llm_client are all reused unchanged. The MCP server exposes that engine
to AI agents (Claude Desktop, Claude Code); this Flask app exposes the same
engine to a human through a browser. Neither interface duplicates logic —
they're two thin adapters over one tested core.

Run with:
    python app.py
Then open http://localhost:5000
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from config import config
from document_processor import answer_question, summarize_document
from file_readers import (
    PathAccessError,
    UnsupportedFileTypeError,
    list_files_in_directory,
    read_file,
)
from llm_client import LLMError
from search_engine import search_folder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("webapp")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25MB upload cap


def _error_response(exc: Exception, status: int = 400):
    return jsonify({"error": str(exc)}), status


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    """Reports whether an LLM backend is actually configured, for the status badge in the UI."""
    llm_ready = bool(config.GROQ_API_KEY) if config.LLM_PROVIDER == "groq" else True
    return jsonify(
        {
            "status": "ok",
            "llm_provider": config.LLM_PROVIDER,
            "llm_ready": llm_ready,
            "base_dir": str(config.BASE_DIR),
        }
    )


@app.route("/api/files")
def api_list_files():
    folder = request.args.get("folder", ".")
    recursive = request.args.get("recursive", "true").lower() != "false"
    try:
        files = list_files_in_directory(folder, recursive)
        return jsonify({"files": [f.__dict__ for f in files]})
    except (PathAccessError, FileNotFoundError, NotADirectoryError) as exc:
        return _error_response(exc, 404)


@app.route("/api/stats")
def api_stats():
    try:
        files = list_files_in_directory(".", recursive=True)
        by_type: dict[str, int] = {}
        total_size = 0
        for f in files:
            if f.is_supported:
                by_type[f.extension] = by_type.get(f.extension, 0) + 1
            total_size += f.size_bytes
        return jsonify(
            {
                "total_files": len(files),
                "supported_files": sum(by_type.values()),
                "total_size_bytes": total_size,
                "by_type": by_type,
            }
        )
    except (PathAccessError, FileNotFoundError) as exc:
        return _error_response(exc, 404)


@app.route("/api/read")
def api_read():
    path = request.args.get("path")
    if not path:
        return _error_response(ValueError("Missing required query param: path"))
    try:
        text = read_file(path)
        return jsonify({"file": path, "characters": len(text), "text": text})
    except (PathAccessError, FileNotFoundError, IsADirectoryError, UnsupportedFileTypeError) as exc:
        return _error_response(exc, 404)


@app.route("/api/search")
def api_search():
    folder = request.args.get("folder", ".")
    keyword = request.args.get("keyword", "")
    recursive = request.args.get("recursive", "true").lower() != "false"
    try:
        df = search_folder(folder, keyword, recursive)
        return jsonify({"keyword": keyword, "files_matched": len(df), "results": df.to_dict(orient="records")})
    except (PathAccessError, FileNotFoundError, ValueError) as exc:
        return _error_response(exc)


@app.route("/api/summarize", methods=["POST"])
def api_summarize():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    style = data.get("style", "concise")
    if not path:
        return _error_response(ValueError("Missing required field: path"))
    try:
        result = summarize_document(path, style)
        return jsonify(result.__dict__)
    except (PathAccessError, FileNotFoundError, IsADirectoryError, UnsupportedFileTypeError) as exc:
        return _error_response(exc, 404)
    except LLMError as exc:
        return _error_response(exc, 502)


@app.route("/api/ask", methods=["POST"])
def api_ask():
    data = request.get_json(silent=True) or {}
    path = data.get("path")
    question = data.get("question")
    if not path or not question:
        return _error_response(ValueError("Missing required fields: path, question"))
    try:
        result = answer_question(path, question)
        return jsonify(result.__dict__)
    except (PathAccessError, FileNotFoundError, IsADirectoryError, UnsupportedFileTypeError) as exc:
        return _error_response(exc, 404)
    except LLMError as exc:
        return _error_response(exc, 502)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return _error_response(ValueError("No file part in request"))
    file = request.files["file"]
    if not file.filename:
        return _error_response(ValueError("No file selected"))

    filename = secure_filename(file.filename)
    ext = Path(filename).suffix.lower()
    if ext not in config.SUPPORTED_EXTENSIONS:
        return _error_response(
            ValueError(f"Unsupported file type '{ext}'. Allowed: {sorted(config.SUPPORTED_EXTENSIONS)}")
        )

    dest = config.BASE_DIR / filename
    file.save(dest)
    logger.info("Uploaded file saved to %s", dest)
    return jsonify({"file": filename, "message": "Upload successful"})


@app.errorhandler(404)
def not_found(_exc):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(exc):
    logger.exception("Unhandled server error")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    config.validate()
    logger.info("Starting AI File Assistant web app. Base directory: %s", config.BASE_DIR)
    app.run(debug=False, host="127.0.0.1", port=5000)
