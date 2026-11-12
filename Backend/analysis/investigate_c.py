"""Capture deterministic BM25 and bi-encoder evidence for C-setting failure review."""
from __future__ import annotations
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retrieve import BM25Retriever, SETTINGS, query_tokens

BASE = Path(__file__).resolve().parents[1]
EXPERIMENTS = BASE / "measurements" / "retrieval_experiments.jsonl"
OUT = BASE / "submission" / "c_failure_retrieval_debug.json"


def compact(chunk: dict) -> dict:
    return {key: chunk.get(key) for key in ("chunk_id", "paper_title", "arxiv_id", "version", "pdf_page", "section", "score", "semantic_score")}


def diagnose(question: str) -> dict:
    retriever = BM25Retriever()
    config = SETTINGS["C-medium-expanded"]
    chunks, index = retriever._corpus(config.query_chunk_words)
    terms = query_tokens(question, chunks)
    scores = index.get_scores(terms)
    ranking = sorted(range(len(chunks)), key=lambda i: float(scores[i]), reverse=True)
    candidates = []
    for index_number in ranking[: config.candidate_k or config.top_k]:
        item = dict(chunks[index_number]); item["score"] = round(float(scores[index_number]), 6)
        candidates.append(item)
    selected = retriever._semantic_rescore(question, candidates, config.top_k)
    return {"question": question, "query_tokens": terms, "bm25_top_8": [compact(c) for c in candidates], "semantic_top_4": [compact(c) for c in selected]}


def main() -> None:
    rows = [json.loads(line) for line in EXPERIMENTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    failures = [row for row in rows if row["source"] == "groq" and row["retrieval_setting"] == "C-medium-expanded" and row["question_number"] in (3, 10)]
    payload = []
    for row in failures:
        item = diagnose(row["result"]["question"])
        item["question_number"] = row["question_number"]
        item["model_result"] = {key: row["result"].get(key) for key in ("answer", "citations", "claims", "refused", "verification", "timing_ms")}
        payload.append(item)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote retrieval diagnostics for {len(payload)} C failures")


if __name__ == "__main__":
    main()
