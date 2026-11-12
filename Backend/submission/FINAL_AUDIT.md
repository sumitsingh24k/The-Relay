# Final audit

| Task | Status | Evidence |
|---|---|---|
| A/B manual review | COMPLETE | `retrieval_review.json`, `manual_grades.json` |
| C failure investigation | COMPLETE | `C_FAILURE_ANALYSIS.md`, `c_failure_retrieval_debug.json`, `correction_q3_run.json` |
| CSV validation | COMPLETE | `CSV_AUDIT.md`, `results_submission_clean.csv`, `csv_id_remaps.json` |
| Groq calibration | COMPLETE | `measurements/groq_baseline.jsonl`, `GROQ_BASELINE_SUMMARY.md` |
| Stand-in calibration | COMPLETE | `standin/calibration.json`, `STANDIN_VALIDATION.md` |
| Streaming/TTFT | COMPLETE | Internal provider SSE and stand-in SSE tested; buffered frontend behavior documented below |
| Retrieval selection | COMPLETE | `RETRIEVAL_COMPARISON.md`, `REQUIRED_TABLES.md` |
| Final report | COMPLETE | `REPORT_FINAL.md` |
| Vaani feedback | BLOCKED | Requires the student's genuine Vaani visit; template is `VAANI_FEEDBACK_TEMPLATE.md` |
| Conversation history | BLOCKED | Requires actual unedited history/reflection; checklist is `CONVERSATION_HISTORY_CHECKLIST.md` |
| Final tests | COMPLETE | Backend: 13 passed; frontend production build passed |
| Secret audit | PARTIAL | `.env` ignored and key not found in source/artifacts; tracked `.venv` must be untracked before committing |

## TTFT and streaming clarification

The provider client requests SSE and records **model TTFT** from request start to first provider token. The stand-in also emits SSE chunks. The `/chat` API intentionally buffers generation, performs claim/citation verification, and returns one JSON response; the React UI therefore does **not** display incremental generated text. Its **user-visible TTFT** is the time until that verified response is returned. This protects grounding. The original brief requires stand-in piece-by-piece behavior and reporting TTFT, but does not require an unverified frontend streaming endpoint.

## Required user actions before final submission

1. Complete `VAANI_FEEDBACK_TEMPLATE.md` from a genuine visit.
2. Add actual assistant conversation history and personal reflection following `CONVERSATION_HISTORY_CHECKLIST.md`.
3. Review the report with your own reasoning and explain the B-medium selection in any live follow-up.
4. Before a Git commit, review then execute `git rm -r --cached .venv` so the virtual environment leaves the Git index; do not delete your local environment.
