import json
import asyncio
from pathlib import Path

from ingest import CHUNKS_PATH, MANIFEST_PATH, REQUIRED_PAPERS, build_chunks, verify_paper
from pipeline import ModelResult, retrieval_only_fallback, run_pipeline, verify_claim_support
from retrieve import BM25Retriever, SETTINGS
from scheduler import AdmissionError, Scheduler, SchedulerConfig


def test_required_pdfs_identify_as_the_required_arxiv_versions():
    verified = [verify_paper(spec) for spec in REQUIRED_PAPERS]
    assert [(item["arxiv_id"], item["version"]) for item in verified] == [
        ("1706.03762", 7),
        ("2410.00037", 1),
        ("2507.07955", 2),
    ]
    assert all(len(item["sha256"]) == 64 for item in verified)


def test_ingestion_writes_manifest_and_page_aware_chunks():
    chunks = build_chunks(chunk_size=120, overlap=20)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert len(manifest["verified_papers"]) == 3
    assert manifest["excluded_files"][0]["first_page_markers"] == ["arXiv:2410.00037v2"]
    assert CHUNKS_PATH.exists()
    assert chunks
    assert {"chunk_id", "paper_title", "arxiv_id", "version", "pdf_page", "section"} <= chunks[0].keys()


def test_bm25_retrieves_transformer_evidence_and_preserves_metadata():
    retriever = BM25Retriever(build_chunks(chunk_size=180, overlap=30))
    results = retriever.retrieve_passages("scaled dot product attention", "B-medium")
    assert results
    assert any(result["arxiv_id"] == "1706.03762" for result in results)
    assert all(result["score"] > 0 for result in results)
    assert set(SETTINGS) == {"A-small", "B-medium", "C-medium-expanded"}


def test_title_aware_query_retrieval_grounds_a_generic_transformer_question():
    retriever = BM25Retriever(build_chunks(chunk_size=180, overlap=30))
    results = retriever.retrieve_passages("what is transformer")
    assert any(result["arxiv_id"] == "1706.03762" and result["pdf_page"] in {1, 2} for result in results)


def test_transformer_dimension_query_does_not_expand_to_moshi_from_generic_model_word():
    retriever = BM25Retriever(build_chunks(chunk_size=500, overlap=75))
    results = retriever.retrieve_passages("What is the base Transformer model dimension?", "C-medium-expanded")
    assert results
    assert all(result["arxiv_id"] == "1706.03762" for result in results)


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    async def generate(self, messages):
        return ModelResult(text=json.dumps(self.payload), model_ttft_ms=12, total_ms=20, tokens_in=10, tokens_out=8)


def test_pipeline_accepts_supported_claim_and_renders_trusted_citation():
    retriever = BM25Retriever(build_chunks(chunk_size=180, overlap=30))
    evidence = retriever.retrieve_passages("scaled dot product attention")[0]
    client = FakeClient({
        "answer": "Scaled dot-product attention is described in the Transformer paper.",
        "claims": [{"text": "Scaled dot-product attention is described in the Transformer paper.", "source_ids": [evidence["chunk_id"]]}],
        "refusal": False,
    })
    result = asyncio.run(run_pipeline("What is scaled dot product attention?", client, retriever))
    assert not result["refused"]
    assert result["verification"] == {"citation_integrity": True, "claim_support": True, "reason": "ok"}
    assert result["citations"][0]["chunk_id"] == evidence["chunk_id"]
    assert result["timing_ms"]["model_ttft"] == 12
    assert result["timing_ms"]["user_visible_ttft"] is not None


def test_pipeline_refuses_fake_citation_or_unsupported_claim():
    retriever = BM25Retriever(build_chunks(chunk_size=180, overlap=30))
    client = FakeClient({
        "answer": "The capital of France is Paris.",
        "claims": [{"text": "The capital of France is Paris.", "source_ids": ["invented-source"]}],
        "refusal": False,
    })
    result = asyncio.run(run_pipeline("What is scaled dot product attention?", client, retriever))
    assert result["refused"]
    assert "not retrieved" in result["answer"]


def test_pipeline_replaces_an_empty_model_refusal_reason_with_a_clear_message():
    retriever = BM25Retriever(build_chunks(chunk_size=180, overlap=30))
    client = FakeClient({"answer": "", "claims": [], "refusal": True})
    result = asyncio.run(run_pipeline("What is scaled dot product attention?", client, retriever))
    assert result["refused"]
    assert "evidence was insufficient" in result["answer"]


def test_claim_support_rejects_an_unrelated_claim_with_a_real_citation():
    retriever = BM25Retriever(build_chunks(chunk_size=180, overlap=30))
    evidence = retriever.retrieve_passages("scaled dot product attention")[0]
    client = FakeClient({"answer": "Paris is the capital of France.", "claims": [{"text": "Paris is the capital of France.", "source_ids": [evidence["chunk_id"]]}], "refusal": False})
    result = asyncio.run(run_pipeline("What is scaled dot product attention?", client, retriever))
    assert result["refused"]


def test_claim_support_rejects_a_changed_number_and_an_unsupported_negation():
    evidence = {"chunk_id": "e1", "text": "The base model uses d_model = 512 and uses attention."}
    numeric_ok, numeric_reason = verify_claim_support(
        [{"text": "The base model dimension is 4096.", "source_ids": ["e1"]}], [evidence]
    )
    negation_ok, negation_reason = verify_claim_support(
        [{"text": "The base model does not use attention.", "source_ids": ["e1"]}], [evidence]
    )
    assert not numeric_ok and "number" in numeric_reason
    assert not negation_ok and "negation" in negation_reason


def test_retrieval_only_fallback_never_invents_a_model_answer():
    chunks = BM25Retriever(build_chunks(chunk_size=180, overlap=30)).retrieve_passages("Transformer")
    result = retrieval_only_fallback("What is a Transformer?", chunks, "test-fallback")
    assert result["fallback"] == "retrieval_only"
    assert result["citations"]
    assert "daily model budget is exhausted" in result["answer"]


def test_scheduler_enforces_quota_queue_deadline_and_bounded_retry():
    async def exercise():
        scheduler = Scheduler(SchedulerConfig(rpm=1, tpm=10, daily_requests=1, daily_tokens=10, max_queue=1, max_retries=1))
        deadline = __import__("time").monotonic() + 5
        await scheduler.admit(estimated_tokens=5, deadline_monotonic=deadline)
        assert scheduler.mode() == "budget_gone"
        try:
            await scheduler.admit(estimated_tokens=1, deadline_monotonic=deadline)
        except AdmissionError as error:
            assert error.code == "daily_budget"
        else:
            raise AssertionError("daily budget must reject a second request")
        await scheduler.enqueue("one", deadline)
        try:
            await scheduler.enqueue("two", deadline)
        except AdmissionError as error:
            assert error.code == "queue_full"
        else:
            raise AssertionError("bounded queue must reject overflow")
        assert await scheduler.retry_delay(0, retry_after_s=0.01) >= 0.25
        try:
            await scheduler.retry_delay(1)
        except AdmissionError as error:
            assert error.code == "retry_exhausted"
        else:
            raise AssertionError("retry budget must stop retries")
    asyncio.run(exercise())


def test_scheduler_workers_process_a_queued_request():
    async def exercise():
        scheduler = Scheduler(SchedulerConfig(max_concurrency=1))
        await scheduler.start()
        try:
            result = await scheduler.submit(lambda: asyncio.sleep(0, result={"status": "ok"}), __import__("time").monotonic() + 2)
            assert result["status"] == "ok"
            assert result["scheduler_timing_ms"]["queue_wait"] >= 0
            assert result["scheduler_timing_ms"]["working"] >= 0
        finally:
            await scheduler.stop()
    asyncio.run(exercise())


def test_scheduler_reconciles_reported_tokens_but_keeps_request_count():
    async def exercise():
        scheduler = Scheduler(SchedulerConfig(rpm=3, tpm=1_000, daily_requests=3, daily_tokens=1_000))
        deadline = __import__("time").monotonic() + 2
        await scheduler.admit(estimated_tokens=500, deadline_monotonic=deadline)
        await scheduler.reconcile_tokens(500, 120)
        assert scheduler._daily_requests == 1
        assert scheduler._daily_tokens == 120
        assert scheduler._tokens_this_minute == 120
    asyncio.run(exercise())
