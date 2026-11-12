# Completion-audit change log

This log records changes made during the final completion audit. Existing raw measurements remain append-only and were not rewritten.

| Change | Reason | Verification |
|---|---|---|
| Added `final_submission_audit.py` and audit reports | Recomputed CSV/table findings directly from retained evidence | Schema, 48 reviewed rows, scenario coverage, and clean-copy consistency checked |
| Added scheduler queue/working timing fields | Historical traces could not split waiting from work | New controlled stand-in trace contains queue wait and working time |
| Added pipeline retry wait accumulation | Retry delay needed explicit future trace evidence | Controlled 429 trace recorded two retries and 2391.264 ms retry wait |
| Moved provider quota admission to each provider call | Retry attempts must count against request limits | `QuotaTrackedClient` is used by `/chat`; tests passed |
| Added actual-token reconciliation | A successful Groq call should replace token estimate when usage exists | Scheduler reconciliation test passed |
| Strengthened claim verification | Citation identity alone could allow altered numbers/negations | Tests reject 4096 when evidence says 512 and unsupported negation |
| Logged failed API admission/provider attempts | One raw row per actual API request requires failures too | Controlled 429 created a `rate_limited` row with retry metadata |
| Added `Frontend/.env` to root `.gitignore`, untracked `.venv`, and untracked the previously tracked frontend env file | Prevent secrets/environment artifacts in submission | Git reports 0 tracked `.venv` and 0 tracked `.env` files; local interpreter and frontend env remain present |
| Replaced Vaani/template placeholders with student-provided notes and conversation reflection | Genuine user input is now available | Feedback, prompts, caught mistake, overruled decision, and student contribution are recorded without invented visit date |
| Added student-provided conversation exports to the portable submission folder | Preserve actual conversation evidence alongside the reflection | PDF and DOCX copies match the recorded SHA-256 hashes |

## Final validation executed

- Backend test suite: **15 passed**.
- Frontend: `npm run lint` and `npm run build` passed.
- Controlled local stand-in: slow response/refusal, HTTP 429 plus Retry-After retry policy, daily-budget retrieval-only fallback.
- No real Groq limit was forced.

## Known evidence limits

- Historic load rows lack run envelope duration, offered rate, peak queue, cost, and full provider TTFT for every row. They are explicitly marked not measured.
- Historic traces cannot be backfilled with queue/working/retry breakdowns.
- A genuine Vaani response and genuine user conversation reflection remain student-provided items.
- No PDF was generated because the environment lacks the mandatory artifact-marker utility required for an auditable PDF workflow.
