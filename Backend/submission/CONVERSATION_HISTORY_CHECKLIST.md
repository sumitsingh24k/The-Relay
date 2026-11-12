# How I worked with the assistant - student reflection

Source: student-provided reflection based on the actual Relay project conversations. The PDF and DOCX exports are registered with hashes in `CONVERSATION_EVIDENCE.md`; attach the original export or screenshots separately if the submission portal requires visual evidence.

## Three important prompts

### 1. Handling multiple concurrent requests - system architecture

> Design a system architecture for handling multiple concurrent users and requests in The Relay. The system should handle traffic bursts, multiple requests executing simultaneously, Groq RPM/TPM/daily limits, failures, timeouts and user cancellations. Explain the queue, workers, concurrency control, rate limiting, retries, deadlines and trade-offs.

This shaped the FastAPI admission controller, bounded request queue, worker pool, semaphore-based concurrency control, RPM/TPM limits, daily quota management, retry policy, and deadline handling.

### 2. RAG architecture - evidence-grounded answers

> Design a RAG-based research assistant that answers questions exclusively using the three approved research papers. Explain PDF ingestion, chunking, BM25 retrieval, evidence sufficiency checking, citation generation, citation integrity and claim-support verification. The assistant must refuse to answer when sufficient supporting evidence is unavailable.

This defined the approved-paper ingestion flow, page-level citations, separate citation-integrity and claim-support checks, and safe refusal behavior.

### 3. Load testing and failure simulation

> Design a testing strategy for The Relay that evaluates steady traffic, burst traffic, sustained overload, reduced RPM limits and daily budget exhaustion. Create a local stand-in model to simulate latency, streaming, HTTP 429/503 failures and retries. Measure TTFT, total latency, token usage, retries and answer correctness.

This guided the controllable local stand-in, five load scenarios, performance measurements, and reproducible evaluation reports.

## One AI mistake I caught

During retrieval testing, the question "What is the base Transformer model dimension?" incorrectly retrieved Moshi and returned 4096 instead of the correct `d_model = 512` from Attention Is All You Need. I checked the retrieved citation against the original paper and found that generic `model` was influencing title-based matching. I requested a correction so only distinctive paper-title terms trigger title matching, and a regression test was added. This showed that a citation must support the actual question, not merely exist.

## One decision where I overruled AI

I chose not to deliberately force rate-limit exhaustion on the real Groq API merely to produce an HTTP 429. That would consume quota and create avoidable provider-side load. Instead, I used real Groq for modest baseline measurements and used a configurable local stand-in to simulate 429, Retry-After, transient failures, latency, and daily budget exhaustion. This separated observed provider behavior from controlled simulated stress tests.

## My distinct contribution

My primary contribution was understanding the assignment requirements, deciding the engineering direction, and validating the implementation. I focused on a single-process reliable RAG assistant constrained to three approved papers, with citation support and safe refusal where evidence is insufficient.

I guided the concurrent-request architecture: bounded queue, workers, semaphore, RPM/TPM limits, daily quotas, retries, deadlines, and failure behavior. I also guided RAG decisions around PDF verification, retrieval settings, evidence verification, and citation integrity. During testing, I reviewed outputs, identified the generic title-matching retrieval bug, compared A/B/C settings, and chose controlled stand-in testing over unnecessarily exhausting real Groq quota. AI coding assistance accelerated implementation, but I directed the approach, reviewed changes, investigated failures, requested corrections, and checked evidence against the brief.
