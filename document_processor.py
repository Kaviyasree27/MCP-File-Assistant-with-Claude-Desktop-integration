"""
Higher-level document intelligence: chunking, summarization, and
question-answering over documents read via file_readers.

Retrieval for Q&A uses a lightweight, dependency-free relevance score
(query-term overlap and frequency) instead of a vector database. That's
a deliberate scope decision for a single-user file assistant: it keeps
the project runnable anywhere Python runs, with no embedding model or
vector store to install, while still doing real retrieval rather than
just dumping the whole document into the prompt. See README.md ("Design
Decisions") for the tradeoffs.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from config import config
from file_readers import read_file
from llm_client import get_llm_client

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-zA-Z0-9']+")


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def chunk_text(text: str, max_words: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
    """Split text into overlapping word-count chunks (keeps context across boundaries)."""
    max_words = max_words or config.CHUNK_WORD_LIMIT
    overlap = overlap or config.CHUNK_OVERLAP
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


def _score_chunk(chunk: str, query_terms: set) -> float:
    tokens = _tokenize(chunk)
    if not tokens:
        return 0.0
    overlap_terms = [t for t in tokens if t in query_terms]
    # frequency of query terms in the chunk, weighted by how many distinct
    # query terms are present (rewards chunks that cover more of the query,
    # not just one repeated word)
    return (len(overlap_terms) / len(tokens)) * len(set(overlap_terms))


def rank_chunks_by_relevance(chunks: List[str], query: str, top_k: int = 4) -> List[str]:
    query_terms = set(_tokenize(query))
    scored = [(chunk, _score_chunk(chunk, query_terms)) for chunk in chunks]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    relevant = [c for c, score in scored if score > 0][:top_k]
    return relevant or chunks[:top_k]  # fall back to first chunks if nothing overlaps


@dataclass
class SummaryResult:
    file_path: str
    summary: str
    chunk_count: int


def summarize_document(file_path: str, style: str = "concise") -> SummaryResult:
    """
    Summarize a document with a map-reduce strategy: long documents are
    chunked, each chunk is summarized independently, then the partial
    summaries are combined into one final summary. Short documents skip
    straight to a single LLM call.
    """
    text = read_file(file_path)
    if not text.strip():
        return SummaryResult(file_path=file_path, summary="(Document has no extractable text.)", chunk_count=0)

    llm = get_llm_client()
    chunks = chunk_text(text)

    style_instruction = {
        "concise": "in 3-5 sentences",
        "detailed": "in a thorough multi-paragraph summary covering all major points",
        "bullets": "as a bulleted list of key points",
    }.get(style, "in 3-5 sentences")

    system = "You are a precise technical document summarizer."

    if len(chunks) <= 1:
        summary = llm.generate(f"Summarize the following document {style_instruction}:\n\n{text}", system=system)
        return SummaryResult(file_path=file_path, summary=summary, chunk_count=len(chunks))

    partial_summaries = []
    for i, chunk in enumerate(chunks, start=1):
        logger.info("Summarizing chunk %d/%d of %s", i, len(chunks), file_path)
        partial = llm.generate(
            f"Summarize this excerpt in 2-3 sentences, preserving key facts:\n\n{chunk}", system=system
        )
        partial_summaries.append(partial)

    combined = "\n".join(f"- {s}" for s in partial_summaries)
    final_prompt = f"Combine these section summaries into a single coherent summary {style_instruction}:\n\n{combined}"
    summary = llm.generate(final_prompt, system=system)

    return SummaryResult(file_path=file_path, summary=summary, chunk_count=len(chunks))


@dataclass
class AnswerResult:
    question: str
    answer: str
    sources: List[str]


def answer_question(file_path: str, question: str, top_k: int = 4) -> AnswerResult:
    """
    Answer a question about a document using retrieval-augmented
    generation: rank chunks by relevance to the question, feed only the
    top-k chunks to the LLM as context, and instruct it to answer only
    from that context (reduces hallucination on long documents).
    """
    text = read_file(file_path)
    if not text.strip():
        return AnswerResult(question=question, answer="The document has no extractable text to answer from.", sources=[])

    chunks = chunk_text(text)
    relevant_chunks = rank_chunks_by_relevance(chunks, question, top_k=top_k) if chunks else [text]

    context = "\n\n---\n\n".join(relevant_chunks)
    prompt = (
        "Answer the question using ONLY the context below. "
        "If the answer isn't in the context, say so explicitly.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )

    llm = get_llm_client()
    answer = llm.generate(
        prompt, system="You are a helpful assistant that answers questions strictly from provided context."
    )

    return AnswerResult(question=question, answer=answer, sources=[file_path])
