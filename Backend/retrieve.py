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
    candidate_k: int | None = None


SETTINGS = {
    "A-small": RetrievalSetting("A-small", 225, 3, "none"),
    "B-medium": RetrievalSetting("B-medium", 500, 5, "none"),
    "C-medium-expanded": RetrievalSetting("C-medium-expanded", 500, 4, "bi-encoder: all-MiniLM-L6-v2", 8),
}


def tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


STOP_WORDS = {"a", "an", "and", "are", "as", "at", "by", "for", "from", "how", "in", "is", "it", "of", "on", "the", "this", "to", "what", "when", "which", "who", "with"}
CORPUS_ALIASES = {"transformer": ["attention"]}
# Generic words must not spuriously anchor every paper title.
TITLE_GENERIC_TERMS = {"model", "models", "paper", "research", "real", "time", "end", "to", "for", "of", "the", "a", "an"}


def query_tokens(query: str, chunks: list[dict]) -> list[str]:
    """Remove question filler words and anchor ambiguous paper-title queries to that paper."""
    terms = [term for term in tokenize(query) if term not in STOP_WORDS]
    for term in tuple(terms):
        terms.extend(alias for alias in CORPUS_ALIASES.get(term, []) if alias not in terms)
    anchors = set(terms)
    titles = {chunk["paper_title"] for chunk in chunks}
    for title in titles:
        title_terms = [term for term in tokenize(title) if term not in STOP_WORDS]
        distinctive_terms = set(title_terms) - TITLE_GENERIC_TERMS
        if anchors & distinctive_terms:
            terms.extend(term for term in title_terms if term not in terms)
    return terms


class BM25Retriever:
    """BM25 baseline plus an optional, genuine bi-encoder re-score for setting C."""
    def __init__(self, chunks: list[dict] | None = None) -> None:
        if chunks is None:
            if not CHUNKS_PATH.exists():
                chunks = build_chunks()
            else:
                chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
        self._chunks_by_size: dict[int, list[dict]] = {500: chunks}
        self._indexes: dict[int, BM25Okapi] = {500: BM25Okapi([tokenize(chunk["text"]) for chunk in chunks])}
        self._bi_encoder = None

    def _corpus(self, chunk_words: int) -> tuple[list[dict], BM25Okapi]:
        if chunk_words not in self._chunks_by_size:
            chunks = build_chunks(chunk_size=chunk_words, overlap=max(30, chunk_words // 6), persist=False)
            self._chunks_by_size[chunk_words] = chunks
            self._indexes[chunk_words] = BM25Okapi([tokenize(chunk["text"]) for chunk in chunks])
        return self._chunks_by_size[chunk_words], self._indexes[chunk_words]

    def _semantic_rescore(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        """True bi-encoder scoring, not a cross-encoder and not BM25 re-labelling."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError("Setting C requires sentence-transformers; install requirements.txt first.") from error
        if self._bi_encoder is None:
            # The explicitly downloaded model is used from cache; retrieval stays offline at runtime.
            self._bi_encoder = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        embeddings = self._bi_encoder.encode([query, *[c["text"] for c in candidates]], normalize_embeddings=True)
        query_embedding, passage_embeddings = embeddings[0], embeddings[1:]
        rescored = []
        for candidate, embedding in zip(candidates, passage_embeddings):
            chunk = dict(candidate)
            chunk["semantic_score"] = round(float(query_embedding @ embedding), 6)
            rescored.append(chunk)
        return sorted(rescored, key=lambda item: item["semantic_score"], reverse=True)[:top_k]

    def retrieve_passages(self, query: str, setting: str = "B-medium") -> list[dict]:
        """Explicit retrieval tool. Returns auditable passages and trusted metadata."""
        if setting not in SETTINGS:
            raise ValueError(f"Unknown retrieval setting {setting!r}; choose from {sorted(SETTINGS)}")
        config = SETTINGS[setting]
        chunks, index = self._corpus(config.query_chunk_words)
        terms = query_tokens(query, chunks)
        if not terms:
            return []
        scores = index.get_scores(terms)
        ranked = sorted(range(len(chunks)), key=lambda index: float(scores[index]), reverse=True)
        selected: list[dict] = []
        # Settings C fetches eight lexical candidates before retaining its best four semantic matches.
        candidate_limit = config.candidate_k or config.top_k
        for index in ranked[:candidate_limit]:
            if scores[index] <= 0:
                continue
            chunk = dict(chunks[index])
            chunk["score"] = round(float(scores[index]), 6)
            chunk["retrieval_setting"] = config.name
            selected.append(chunk)
        if config.candidate_k:
            selected = self._semantic_rescore(query, selected, config.top_k)
        return selected


_default_retriever: BM25Retriever | None = None


def retrieve_passages(query: str, setting: str = "B-medium") -> list[dict]:
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = BM25Retriever()
    return _default_retriever.retrieve_passages(query, setting)
