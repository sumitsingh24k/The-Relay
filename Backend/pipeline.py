"""Grounded Relay request pipeline with a conservative evidence gate and verifier."""

from __future__ import annotations

import asyncio
import json
import re
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from retrieve import BM25Retriever, tokenize


MAX_RETRIEVAL_ATTEMPTS = 2
MAX_MODEL_RETRIES = 2
MAX_QUESTION_CHARS = 1_000
MIN_EVIDENCE_SCORE = 1.0


@dataclass
class ModelResult:
    text: str
    model_ttft_ms: float | None
    total_ms: float
    tokens_in: int | None = None
    tokens_out: int | None = None
    provider_headers: dict[str, str] = field(default_factory=dict)


class ModelClient(Protocol):
    async def generate(self, messages: list[dict[str, str]]) -> ModelResult: ...


class DailyProviderBudgetError(RuntimeError):
    """The provider indicated a day-scale quota reset; retrying cannot help this request."""


def normalize_question(question: str) -> str:
    normalized = " ".join(question.split())
    if not normalized:
        raise ValueError("Question must not be empty.")
    if len(normalized) > MAX_QUESTION_CHARS:
        raise ValueError(f"Question exceeds {MAX_QUESTION_CHARS} characters.")
    return normalized


def source_label(chunk: dict[str, Any]) -> str:
    return (
        f"[{chunk['chunk_id']}] {chunk['paper_title']}, arXiv:{chunk['arxiv_id']}v{chunk['version']}, "
        f"PDF p. {chunk['pdf_page']}, {chunk['section']}"
    )


def evidence_is_sufficient(chunks: list[dict[str, Any]]) -> bool:
    return bool(chunks) and max(float(chunk["score"]) for chunk in chunks) >= MIN_EVIDENCE_SCORE


def prompt_for(question: str, chunks: list[dict[str, Any]]) -> list[dict[str, str]]:
    evidence = "\n\n".join(f"{source_label(chunk)}\n{chunk['text']}" for chunk in chunks)
    return [
        {
            "role": "system",
            "content": (
                "Answer only from the supplied evidence. Return valid JSON with exactly: "
                "answer (string), claims (array of {text, source_ids}), refusal (boolean). "
                "Every factual claim must cite one or more supplied chunk IDs. If evidence is insufficient, "
                "set refusal=true, claims=[] and do not guess."
            ),
        },
        {"role": "user", "content": f"Question: {question}\n\nEvidence:\n{evidence}"},
    ]


def refusal(question: str, reason: str, request_id: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "status": "ok",
        "answer": f"I cannot verify an answer from the approved papers: {reason}",
        "citations": [],
        "claims": [],
        "refused": True,
        "verification": {"citation_integrity": True, "claim_support": True, "reason": reason},
        "question": question,
    }


def parse_draft(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("answer"), str):
        return None
    if not isinstance(parsed.get("claims", []), list) or not isinstance(parsed.get("refusal"), bool):
        return None
    return parsed


def verify_citation_integrity(claims: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> tuple[bool, str]:
    available = {chunk["chunk_id"] for chunk in chunks}
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("text"), str):
            return False, "claim structure is invalid"
        source_ids = claim.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            return False, "a factual claim is missing a citation"
        if any(not isinstance(source_id, str) or source_id not in available for source_id in source_ids):
            return False, "claim cites a source that was not retrieved"
    return True, "ok"


def _meaningful_terms(value: str) -> set[str]:
    stop_words = {"the", "a", "an", "is", "are", "of", "to", "and", "in", "for", "that", "with", "this", "it"}
    return {term for term in tokenize(value) if len(term) > 2 and term not in stop_words}


def verify_claim_support(claims: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> tuple[bool, str]:
    """Check support separately from citation ID validity; reject weakly grounded claims conservatively."""
    by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    for claim in claims:
        claim_terms = _meaningful_terms(claim["text"])
        if not claim_terms:
            return False, "claim has no verifiable content"
        evidence_terms: set[str] = set()
        evidence_text = ""
        for source_id in claim["source_ids"]:
            evidence_terms |= _meaningful_terms(by_id[source_id]["text"])
            evidence_text += " " + by_id[source_id]["text"].lower()
        overlap = len(claim_terms & evidence_terms) / len(claim_terms)
        # Lexical support is conservative but not synonym-blind. Source identity is checked separately above.
        if overlap < 0.15:
            return False, "citation exists but does not sufficiently support the claim"
        # Lexical overlap alone can wrongly approve a contradictory numeric claim
        # (for example, "512" changed to "4096"). Every stated number must occur
        # in the cited evidence. This intentionally refuses number-normalization
        # claims rather than guessing conversions.
        claim_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", claim["text"]))
        evidence_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", evidence_text))
        if claim_numbers and not claim_numbers <= evidence_numbers:
            return False, "citation does not support the claim's stated number"
        # A source that never expresses a negation cannot safely support a newly
        # introduced negative assertion. This is deliberately conservative.
        claim_negations = {"no", "not", "never", "without", "cannot", "isnt", "doesnt", "dont"} & _meaningful_terms(claim["text"])
        evidence_negations = {"no", "not", "never", "without", "cannot", "isnt", "doesnt", "dont"} & _meaningful_terms(evidence_text)
        if claim_negations and not claim_negations <= evidence_negations:
            return False, "citation does not support the claim's negation"
    return True, "ok"


def render_citations(claims: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    ids = []
    for claim in claims:
        ids.extend(claim["source_ids"])
    return [
        {
            "chunk_id": source_id,
            "paper": by_id[source_id]["paper_title"],
            "arxiv_id": by_id[source_id]["arxiv_id"],
            "version": by_id[source_id]["version"],
            "pdf_page": by_id[source_id]["pdf_page"],
            "section": by_id[source_id]["section"],
        }
        for source_id in dict.fromkeys(ids)
    ]


def retrieval_only_fallback(question: str, chunks: list[dict[str, Any]], request_id: str) -> dict[str, Any]:
    """No model call: quote only the local evidence when daily model budget is exhausted."""
    citations = [
        {"chunk_id": c["chunk_id"], "paper": c["paper_title"], "arxiv_id": c["arxiv_id"], "version": c["version"], "pdf_page": c["pdf_page"], "section": c["section"]}
        for c in chunks[:3]
    ]
    passages = "\n\n".join(f"{source_label(c)}\n{c['text'][:500]}" for c in chunks[:3])
    return {"request_id": request_id, "status": "ok", "answer": "The daily model budget is exhausted, so I cannot generate a verified synthesis. These retrieved passages may help:\n\n" + passages, "citations": citations, "claims": [], "refused": True, "verification": {"citation_integrity": True, "claim_support": False, "reason": "daily model budget exhausted; retrieval-only fallback"}, "question": question, "fallback": "retrieval_only"}


async def run_pipeline(
    question: str,
    client: ModelClient,
    retriever: BM25Retriever | None = None,
    retrieval_setting: str = "B-medium",
) -> dict[str, Any]:
    """Seven-stage flow: normalize, retrieve, gate, bounded re-retrieve, draft, verify, return/log-ready."""
    started = time.perf_counter()
    request_id = f"req-{uuid.uuid4().hex[:12]}"
    normalized = normalize_question(question)
    retriever = retriever or BM25Retriever()
    chunks: list[dict[str, Any]] = []

    for attempt in range(MAX_RETRIEVAL_ATTEMPTS):
        chunks = retriever.retrieve_passages(normalized, retrieval_setting)
        if evidence_is_sufficient(chunks):
            break
        if attempt == MAX_RETRIEVAL_ATTEMPTS - 1:
            result = refusal(normalized, "retrieved evidence was insufficient", request_id)
            result["timing_ms"] = {"model_ttft": None, "user_visible_ttft": None, "total": round((time.perf_counter() - started) * 1000, 3)}
            result["retrieval_attempts"] = attempt + 1
            result["retrieval_setting"] = retrieval_setting
            return result

    retries = 0
    retry_wait_ms = 0.0
    while True:
        try:
            model_result = await client.generate(prompt_for(normalized, chunks))
            break
        except Exception as error:
            status = getattr(error, "status_code", None)
            headers = getattr(error, "headers", {})
            error_text = str(error).lower()
            retry_after = headers.get("retry-after")
            if status == 429 and ("daily" in error_text or (retry_after and float(retry_after) >= 3600)):
                raise DailyProviderBudgetError("provider daily budget exhausted") from error
            transient = status == 429 or (isinstance(status, int) and 500 <= status < 600)
            if not transient or retries >= MAX_MODEL_RETRIES:
                # Preserve observed retry metadata even when the request ultimately
                # fails, so CSV/trace error rows are not misleadingly recorded as 0.
                setattr(error, "relay_retries", retries)
                setattr(error, "relay_retry_wait_ms", round(retry_wait_ms, 3))
                raise
            try:
                wait_s = float(retry_after) if retry_after else 0.25 * (2**retries)
            except ValueError:
                wait_s = 0.25 * (2**retries)
            # Bounded exponential backoff with jitter avoids synchronized retry storms.
            delay_s = wait_s + random.uniform(0, max(0.01, wait_s * 0.25))
            await asyncio.sleep(delay_s)
            retry_wait_ms += delay_s * 1000
            retries += 1
    draft = parse_draft(model_result.text)
    if draft is None:
        result = refusal(normalized, "model response was not valid structured grounded output", request_id)
    elif draft["refusal"]:
        result = refusal(normalized, draft["answer"].strip() or "the model declined because the evidence was insufficient", request_id)
    else:
        integrity_ok, integrity_reason = verify_citation_integrity(draft["claims"], chunks)
        support_ok, support_reason = (False, "not evaluated")
        if integrity_ok:
            support_ok, support_reason = verify_claim_support(draft["claims"], chunks)
        if not integrity_ok or not support_ok:
            result = refusal(normalized, integrity_reason if not integrity_ok else support_reason, request_id)
        else:
            result = {
                "request_id": request_id,
                "status": "ok",
                "answer": draft["answer"],
                "citations": render_citations(draft["claims"], chunks),
                "claims": draft["claims"],
                "refused": False,
                "verification": {"citation_integrity": True, "claim_support": True, "reason": "ok"},
                "question": normalized,
            }
    # User-visible streaming deliberately begins after verification, unlike upstream model TTFT.
    total_ms = round((time.perf_counter() - started) * 1000, 3)
    result["timing_ms"] = {
        "model_ttft": model_result.model_ttft_ms,
        "user_visible_ttft": total_ms if not result["refused"] else None,
        "total": total_ms,
        "model_total": model_result.total_ms,
    }
    result["usage"] = {"tokens_in": model_result.tokens_in, "tokens_out": model_result.tokens_out}
    result["retrieval_attempts"] = attempt + 1
    result["retries"] = retries
    result["retry_wait_ms"] = round(retry_wait_ms, 3)
    result["retrieval_setting"] = retrieval_setting
    return result
