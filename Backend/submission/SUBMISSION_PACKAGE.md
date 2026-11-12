# Submission package checklist

## Include in the final upload

- Backend source code and `requirements.txt`.
- Frontend source code and `package.json`; exclude `node_modules`, `dist`, `.env`, and `.venv`.
- `data/papers/manifest.json`, `data/index/chunks.json`, and required papers if the portal permits source PDFs.
- `results.csv` as immutable raw evidence and `submission/results_submission_clean.csv` as the documented clean copy.
- `trace.jsonl`, `measurements/`, `evaluation/questions.json`, `evaluation/manual_grades.json`, and analysis scripts.
- `submission/REQUIRED_TABLES.md`, `AUDIT_TABLES.md`, `RETRIEVAL_COMPARISON.md`, `C_FAILURE_ANALYSIS.md`, and `STANDIN_VALIDATION.md`.
- `submission/REPORT_TWO_PAGE_SOURCE.md` as the final report source, plus an exported two-page PDF once it has been generated and visually reviewed.
- `submission/VAANI_FEEDBACK_TEMPLATE.md`, `CONVERSATION_HISTORY_CHECKLIST.md`, `CONVERSATION_EVIDENCE.md`, and `conversation_evidence/`.

## Do not include

- Any `.env` file, API key, token, `.venv`, `node_modules`, or generated frontend `dist` directory.

## Final human checks before upload

1. Export `REPORT_TWO_PAGE_SOURCE.md` to a PDF and confirm it is exactly two pages with legible tables.
2. If required by the portal, attach the conversation PDF/DOCX in `conversation_evidence/`.
3. Confirm the final archive contains no secrets.
