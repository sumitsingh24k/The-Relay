# Implementation audit

## Completed requirements

- Exact three-paper corpus is verified by first-page arXiv marker, title, SHA-256, page count, and manifest.
- Page-aware PyMuPDF extraction, overlapping chunking, BM25 retrieval, citations, evidence gate, safe refusal, and bounded re-retrieval are implemented.
- Claim support is checked separately from citation-ID integrity.
- Real Groq and local OpenAI-compatible stand-in share a client interface.
- Single-process admission control includes bounded queue, workers, semaphore, deadlines, RPM/TPM/daily counters, Retry-After-aware bounded backoff, and jitter.
- Stand-in supports delay, 503 failure, 429 Retry-After, quota exhaustion, concurrency slowdown, and SSE pieces.
- Exact raw CSV schema is present and raw results are preserved.
- Five named load scenarios, 8 real Groq baseline calls, and 48 real Groq A/B/C evaluation calls were run.
- A/B/C manual review, C failure analysis, retrieval selection, CSV audit, and tested frontend build are present.

## Partially completed requirements

- Load raw data records outcomes and latency but does not record per-run offered duration/rate or peak queue, so those table cells are honestly marked `not measured`.
- Model TTFT is measured. The backend buffers and verifies the full answer before replying, so user-visible TTFT is response-delivery time, not token streaming time.
- Real provider headers exposed RPD and TPM values for the active model. RPM, TPD, concurrent-request limit, and real 429 recovery were not measured.

## Missing or external evidence

- Genuine Vaani feedback.
- Actual unedited assistant conversation history/prompts and the student's own reflection.
- A real Groq 429/recovery observation, deliberately not forced to avoid abusing quota.

## Bugs/inconsistencies found and action

- C originally fetched only four candidates despite its documented top-eight design; corrected in `retrieve.py`.
- Generic title expansion allowed `model` to anchor Moshi for a Transformer question; corrected and regression-tested.
- Raw `results.csv` has duplicate IDs from repeated load-driver attempts and sparse timing/token fields. It is retained; a remapped clean copy and audit are supplied.
- Frontend is functional but uses one dense `App.jsx`; empty component/page files are unused placeholders.
- The Git index currently contains `.venv` despite the new root ignore rule. Do not commit it again; run `git rm -r --cached .venv` only after reviewing the staged removal.

## Files changed for the remaining work

- Retrieval correction: `retrieve.py`, `tests/test_pipeline.py`.
- Evaluation/grades: `evaluation/manual_grades.json`, `evaluation/grade_review.py`.
- Evidence scripts: `analysis/audit_results.py`, `analysis/investigate_c.py`, `analysis/generate_submission_tables.py`, `analysis/summarize_groq_baseline.py`.
- Submission evidence: files under `submission/`.

## Execution order used

1. Inspect source, artifacts, PDF corpus, tests, and logs.
2. Grade A/B/C existing real results.
3. Diagnose C failures, correct proven retrieval bug, and regression-test it.
4. Add five paced Groq calibration calls and recalibrate/test the stand-in.
5. Validate raw CSV without overwriting it; create a clean mapped copy.
6. Generate comparison, required tables, report, and final audit.
