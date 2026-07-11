"""
LLM client abstraction.

Two interchangeable backends, selected via config.LLM_PROVIDER, both
implementing the same generate(prompt) -> str interface so the rest of
the app is provider-agnostic:

  - "groq"   Groq's free-tier hosted inference API (OpenAI-compatible
             chat completions). Fast, no local compute needed.
  - "ollama" A fully local model served by Ollama. No API key, no
             external network call, works offline.

This is a small Strategy pattern: swapping providers is a one-line env
var change, and adding a third backend (e.g. Gemini) means adding one
class without touching document_processor.py or server.py.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

import requests

from config import config

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised for any LLM backend failure (network, auth, bad response)."""


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """Send a prompt to the model and return its text response."""


class GroqClient(LLMClient):
    def __init__(self) -> None:
        if not config.GROQ_API_KEY:
            raise LLMError(
                "GROQ_API_KEY is not set. Get a free key at "
                "https://console.groq.com/keys and add it to your .env file, "
                "or set MCP_LLM_PROVIDER=ollama for a fully local, key-free setup."
            )

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = requests.post(
                config.GROQ_API_URL,
                headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
                json={
                    "model": config.GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": config.LLM_MAX_TOKENS,
                    "temperature": 0.3,
                },
                timeout=config.LLM_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.RequestException as exc:
            raise LLMError(f"Groq API request failed: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected Groq API response format: {exc}") from exc


class OllamaClient(LLMClient):
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        try:
            response = requests.post(
                f"{config.OLLAMA_BASE_URL}/api/generate",
                json={"model": config.OLLAMA_MODEL, "prompt": full_prompt, "stream": False},
                timeout=config.LLM_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response.json()["response"].strip()
        except requests.RequestException as exc:
            raise LLMError(
                f"Could not reach Ollama at {config.OLLAMA_BASE_URL}. Is 'ollama serve' "
                f"running, and have you run 'ollama pull {config.OLLAMA_MODEL}'? "
                f"Original error: {exc}"
            ) from exc
        except KeyError as exc:
            raise LLMError(f"Unexpected Ollama response format: {exc}") from exc


def get_llm_client() -> LLMClient:
    if config.LLM_PROVIDER == "groq":
        return GroqClient()
    if config.LLM_PROVIDER == "ollama":
        return OllamaClient()
    raise LLMError(f"Unknown LLM provider: {config.LLM_PROVIDER}")
