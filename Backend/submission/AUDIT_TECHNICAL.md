# Task 5: technical audits

## Streaming - PASS WITH DESIGN LIMITATION

Groq and the stand-in use SSE upstream. The backend consumes the complete stream, verifies claims and citations, then returns JSON. Therefore the React frontend does not receive unverified incremental answer chunks. Provider-model TTFT and frontend-visible delivery time are distinct and recorded separately where available.

## Rate-limit accounting - PARTIALLY PASSING, IMPROVED

Each `generate()` attempt is now wrapped by `QuotaTrackedClient`, so retries are independently admitted and count as request attempts. Successful calls with reported usage reconcile the 1000-token reservation to actual input plus output tokens. The stand-in has no real usage data and remains conservatively charged at its reservation. Failed provider calls retain their reservation because actual usage is unknown.

## Claim verification - PASS WITH STATED LIMIT

Citation identity and support are separate checks. New tests reject a changed number (4096 when evidence says 512) and an unsupported negation. The verifier remains lexical/conservative, not a natural-language-entailment model, so nuanced paraphrases can still be refused.

## Scheduler concurrency and persistence - PASS

The scheduler uses an async lock around quota counters, a bounded `asyncio.Queue`, worker pool, semaphore, deadlines, and daily JSON persistence. New worker timing fields separate queue wait from worker time for future traces. Existing tests cover quota, queue overflow, deadlines, workers, retry bounds, and reconciliation.

## CSV and metrics integrity - PARTIAL

The exact schema and status values are valid. Raw duplicate IDs and missing historical fields are preserved and documented; clean copy remaps duplicate IDs. Historical `first_token_ms` is frontend-visible post-verification time, not a provider TTFT field. Future trace rows include richer timing details; past values are not reconstructed.
