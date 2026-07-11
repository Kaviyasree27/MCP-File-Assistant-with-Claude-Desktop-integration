"""
Keyword search across a folder of documents.

Uses pandas to assemble and rank results, which keeps "most relevant
file first" trivial and gives a clean tabular structure that serializes
cleanly back to an MCP client.
"""

from __future__ import annotations

import logging
import re
from typing import List

import pandas as pd

from file_readers import PathAccessError, UnsupportedFileTypeError, list_files_in_directory, read_file

logger = logging.getLogger(__name__)


def _find_snippets(text: str, keyword: str, context_chars: int = 80) -> List[str]:
    snippets = []
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    for match in pattern.finditer(text):
        start = max(match.start() - context_chars, 0)
        end = min(match.end() + context_chars, len(text))
        snippet = text[start:end].replace("\n", " ").strip()
        snippets.append(f"...{snippet}...")
    return snippets


def search_folder(
    folder_path: str,
    keyword: str,
    recursive: bool = True,
    max_snippets_per_file: int = 5,
) -> pd.DataFrame:
    """
    Search every supported document under folder_path for `keyword`.

    Returns a DataFrame with columns: file, match_count, snippets,
    sorted by match_count descending. Files that fail to read (corrupt,
    password-protected, unsupported) are skipped and logged, not fatal.
    """
    if not keyword.strip():
        raise ValueError("keyword must not be empty")

    files = [f for f in list_files_in_directory(folder_path, recursive) if f.is_supported]
    rows = []

    for f in files:
        try:
            text = read_file(f.path)
        except (UnsupportedFileTypeError, PathAccessError) as exc:
            logger.warning("Skipping %s: %s", f.path, exc)
            continue
        except Exception as exc:  # noqa: BLE001 - one bad file shouldn't kill the whole search
            logger.warning("Failed to read %s: %s", f.path, exc)
            continue

        snippets = _find_snippets(text, keyword)
        if snippets:
            rows.append(
                {
                    "file": f.path,
                    "match_count": len(snippets),
                    "snippets": snippets[:max_snippets_per_file],
                }
            )

    df = pd.DataFrame(rows, columns=["file", "match_count", "snippets"])
    if not df.empty:
        df = df.sort_values("match_count", ascending=False).reset_index(drop=True)
    return df
