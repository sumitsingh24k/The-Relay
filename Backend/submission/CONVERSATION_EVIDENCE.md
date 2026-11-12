# Conversation evidence register

The student supplied these actual conversation exports on 12 November 2026. Portable copies are included in `submission/conversation_evidence/` for submission.

| Evidence | Original location | SHA-256 | What it supports |
|---|---|---|---|
| Conversation PDF | `conversation_evidence/chatgpt_conversation.pdf` | `c364a4c1c4b0df92d26a1911c6040139571aaf7cac621f4efd8f86c45fe2da7c` | Reflection content, Vaani discussion, report review, and submission decisions. |
| Conversation DOCX | `conversation_evidence/chatgpt_conversation.docx` | `eb2bdf7096200d4d8598ad48e99c66c3c11a1969f26d08765cc41d77ee827c0e` | Readable transcript of the same project conversation. |

## Relevant discussion captured

1. Concurrent-request architecture: bounded queue, workers, semaphore, quotas, retries, deadlines, and traffic spikes.
2. Evidence-grounded RAG: exact PDFs, ingestion, BM25, page citations, claim support, and safe refusal.
3. Stand-in/load testing: five scenarios, 429/503 behavior, streaming, retry policy, and measurement outputs.
4. Error review: Transformer dimension was incorrectly answered with Moshi's 4096 before generic title expansion was fixed; the correct Transformer `d_model` is 512.
5. Student decision: do not deliberately exhaust real Groq quota; use modest real baseline measurements and controlled stand-in fault injection.

The reflection in `CONVERSATION_HISTORY_CHECKLIST.md` is a concise student-facing summary of these records. Do not describe reconstructed prompts as verbatim quotations; the evidence contains both original user prompts and later report-ready reconstructions.
