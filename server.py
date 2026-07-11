"""
MCP File Assistant server.

Exposes file-system and document-intelligence operations as MCP tools so
any MCP-compatible client (Claude Desktop, Claude Code, or a custom
agent) can browse, search, summarize, and ask questions about local
documents (PDF, DOCX, XLSX, TXT).

Run directly for stdio transport (used by Claude Desktop):
    python server.py
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from config import config
from document_processor import answer_question, summarize_document
from file_readers import (
    PathAccessError,
    UnsupportedFileTypeError,
    delete_all_files as _delete_all_files,
    delete_file as _delete_file,
    list_files_in_directory,
    read_file,
)
from llm_client import LLMError
from search_engine import search_folder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp_file_assistant")

mcp = FastMCP("file-assistant")


@mcp.tool()
def list_files(folder_path: str = ".", recursive: bool = True) -> dict:
    """
    List files in a folder within the allowed base directory.

    Args:
        folder_path: Path relative to the configured base directory (default: root).
        recursive: Whether to include files in subfolders.

    Returns:
        A dict with the folder queried and a list of file entries
        (name, path, extension, size_bytes, modified, is_supported).
    """
    try:
        files = list_files_in_directory(folder_path, recursive)
        return {"folder": folder_path, "count": len(files), "files": [f.__dict__ for f in files]}
    except (PathAccessError, FileNotFoundError, NotADirectoryError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def read_document(file_path: str) -> dict:
    """
    Read and extract plain text from a PDF, DOCX, XLSX or TXT file.

    Args:
        file_path: Path to the file, relative to the base directory.

    Returns:
        A dict with the extracted text and character count, or an error message.
    """
    try:
        text = read_file(file_path)
        return {"file": file_path, "characters": len(text), "text": text}
    except (PathAccessError, FileNotFoundError, IsADirectoryError, UnsupportedFileTypeError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def search_documents(folder_path: str, keyword: str, recursive: bool = True) -> dict:
    """
    Search for a keyword across all supported documents in a folder.

    Args:
        folder_path: Folder to search, relative to the base directory.
        keyword: Text to search for (case-insensitive).
        recursive: Whether to search subfolders too.

    Returns:
        A dict with matching files ranked by match count, each including
        a few context snippets around the match.
    """
    try:
        df = search_folder(folder_path, keyword, recursive)
        return {
            "folder": folder_path,
            "keyword": keyword,
            "files_matched": len(df),
            "results": df.to_dict(orient="records"),
        }
    except (PathAccessError, FileNotFoundError, ValueError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def summarize(file_path: str, style: str = "concise") -> dict:
    """
    Summarize a document using an LLM.

    Args:
        file_path: Path to the file to summarize.
        style: One of "concise", "detailed", or "bullets".

    Returns:
        A dict with the generated summary and how many chunks it was built from.
    """
    try:
        return summarize_document(file_path, style).__dict__
    except (PathAccessError, FileNotFoundError, IsADirectoryError, UnsupportedFileTypeError) as exc:
        return {"error": str(exc)}
    except LLMError as exc:
        return {"error": f"LLM error: {exc}"}


@mcp.tool()
def ask_document(file_path: str, question: str) -> dict:
    """
    Answer a question about a specific document's contents using an LLM,
    grounded in the most relevant sections of the document (RAG-style
    retrieval, no external vector database required).

    Args:
        file_path: Path to the file to query.
        question: A natural-language question about the document.

    Returns:
        A dict with the answer and the source file it was grounded in.
    """
    try:
        return answer_question(file_path, question).__dict__
    except (PathAccessError, FileNotFoundError, IsADirectoryError, UnsupportedFileTypeError) as exc:
        return {"error": str(exc)}
    except LLMError as exc:
        return {"error": f"LLM error: {exc}"}


@mcp.tool()
def delete_file(file_path: str) -> dict:
    """
    Permanently delete a single file within the allowed base directory.
    This cannot be undone — there is no recycle bin behavior here.

    Args:
        file_path: Path to the file to delete, relative to the base directory.

    Returns:
        A dict confirming what was deleted, or an error message.
    """
    try:
        _delete_file(file_path)
        return {"deleted": file_path}
    except (PathAccessError, FileNotFoundError, IsADirectoryError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def delete_all_files(folder_path: str = ".", confirm: bool = False) -> dict:
    """
    Permanently delete every supported document in a folder.

    Requires confirm=True as an explicit safety gate — a vague request
    like "clean up my files" should NOT be enough to trigger this. Only
    call with confirm=True when the user has clearly and explicitly asked
    to delete everything.

    Args:
        folder_path: Folder to clear, relative to the base directory.
        confirm: Must be explicitly set to True to actually perform the deletion.

    Returns:
        A dict with the count and list of deleted files, or an error message.
    """
    if not confirm:
        return {"error": "Refusing to delete all files without confirm=True. This is a safety check, not a bug."}
    try:
        deleted = _delete_all_files(folder_path, recursive=True)
        return {"deleted_count": len(deleted), "deleted": deleted}
    except (PathAccessError, FileNotFoundError) as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    config.validate()
    logger.info("Starting MCP File Assistant. Base directory: %s", config.BASE_DIR)
    mcp.run(transport="stdio")
