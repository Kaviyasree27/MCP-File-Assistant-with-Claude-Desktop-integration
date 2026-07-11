"""
Configuration management for the MCP File Assistant.

Centralizes all environment-driven settings so the rest of the codebase
never touches os.environ directly. This makes the app easy to reconfigure
for different environments (dev, demo, production) without touching code.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- File access ------------------------------------------------
    # Root directory the assistant is allowed to read from. Every
    # incoming path is resolved against this and validated so a caller
    # can never read files outside of it (path traversal protection).
    BASE_DIR: Path = Path(os.getenv("MCP_FILES_BASE_DIR", str(Path.cwd()))).resolve()

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".txt"}

    # --- Chunking (for summarization / Q&A retrieval) -----------------
    CHUNK_WORD_LIMIT: int = int(os.getenv("MCP_CHUNK_WORD_LIMIT", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("MCP_CHUNK_OVERLAP", "50"))

    # --- LLM provider --------------------------------------------------
    # "groq"   -> free-tier hosted inference, needs GROQ_API_KEY
    # "ollama" -> fully local model, no API key required at all
    LLM_PROVIDER: str = os.getenv("MCP_LLM_PROVIDER", "groq").lower()

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    LLM_TIMEOUT_SECONDS: int = int(os.getenv("MCP_LLM_TIMEOUT", "60"))
    LLM_MAX_TOKENS: int = int(os.getenv("MCP_LLM_MAX_TOKENS", "1024"))

    @classmethod
    def validate(cls) -> None:
        if not cls.BASE_DIR.exists():
            raise FileNotFoundError(f"BASE_DIR does not exist: {cls.BASE_DIR}")
        if cls.LLM_PROVIDER not in {"groq", "ollama"}:
            raise ValueError(f"Unsupported MCP_LLM_PROVIDER: {cls.LLM_PROVIDER}")


config = Config()
