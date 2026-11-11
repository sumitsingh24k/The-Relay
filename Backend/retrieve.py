"""BM25 retrieval tool for the verified Relay corpus."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from ingest import CHUNKS_PATH, build_chunks


@dataclass(frozen=True)
class RetrievalSetting:
    name: str
    query_chunk_words: int
    top_k: int
    rescoring: str


SETTINGS = {
    "A-small": RetrievalSetting("A-small", 200, 3, "none"),
    "B-medium": RetrievalSetting("B-medium", 500, 5, "none"),
    # This deliberately remains lexical until a separately measured bi-encoder is added.
    "C-medium-expanded": RetrievalSetting("C-medium-expanded", 500, 8, "none (baseline; semantic re-scoring not installed)"),
}


def tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


STOP_WORDS = {"a", "an", "and", "are", "as", "at", "by", "for", "from", "how", "in", "is", "it", "of", "on", "the", "this", "to", "what", "when", "which", "who", "with"}
CORPUS_ALIASES = {"transformer": ["attention"]}


def query_tokens(query: str, chunks: list[dict]) -> list[str]:
    """Remove question filler words and anchor ambiguous paper-title queries to that paper."""
    terms = [term for term in tokenize(query) if term not in STOP_WORDS]
    for term in tuple(terms):
        terms.extend(alias for alias in CORPUS_ALIASES.get(term, []) if alias not in terms)
    titles = {chunk["paper_title"] for chunk in chunks}
    for title in titles:
        title_terms = [term for term in tokenize(title) if term not in STOP_WORDS]
        if set(terms) & set(title_terms):
            terms.extend(term for term in title_terms if term not in terms)
    return terms


class BM25Retriever:
    def __init__(self, chunks: list[dict] | None = None) -> None:
        if chunks is None:
            if not CHUNKS_PATH.exists():
                chunks = build_chunks()
            else:
                chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
        self.chunks = chunks
        self.index = BM25Okapi([tokenize(chunk["text"]) for chunk in chunks])

    def retrieve_passages(self, query: str, setting: str = "B-medium") -> list[dict]:
        """Explicit retrieval tool. Returns auditable passages and trusted metadata."""
        if setting not in SETTINGS:
            raise ValueError(f"Unknown retrieval setting {setting!r}; choose from {sorted(SETTINGS)}")
        terms = query_tokens(query, self.chunks)
        if not terms:
            return []
        config = SETTINGS[setting]
        scores = self.index.get_scores(terms)
        ranked = sorted(range(len(self.chunks)), key=lambda index: float(scores[index]), reverse=True)
        selected: list[dict] = []
        for index in ranked[: config.top_k]:
            if scores[index] <= 0:
                continue
            chunk = dict(self.chunks[index])
            chunk["score"] = round(float(scores[index]), 6)
            chunk["retrieval_setting"] = config.name
            selected.append(chunk)
        return selected


_default_retriever: BM25Retriever | None = None


def retrieve_passages(query: str, setting: str = "B-medium") -> list[dict]:
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = BM25Retriever()
    return _default_retriever.retrieve_passages(query, setting)
