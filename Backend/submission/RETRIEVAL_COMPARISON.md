# Retrieval comparison and selection

## Same evaluation set

Each setting used the same 16 questions: 12 answerable questions from the three approved papers and four deliberately unanswerable questions. All 48 provider runs are recorded in `measurements/retrieval_experiments.jsonl`; manual grades and explanations are in `retrieval_review.json`.

| Setting | Configuration | Correct cited | Wrong | Correctly refused | Selection note |
|---|---|---:|---:|---:|---|
| A-small | ~225-word chunks, top 3 BM25 | 10/16 (62.5%) | 2/16 (12.5%) | 4/16 (25.0%) | Missed the answerable Moshi latency question; also confused the Transformer dimension. |
| B-medium | 500-word chunks, top 5 BM25 | 11/16 (68.8%) | 1/16 (6.3%) | 4/16 (25.0%) | Best reviewed accuracy and safe-refusal rate. |
| C-medium-expanded | 500-word chunks, BM25 top 8 then MiniLM bi-encoder retain 4 | 10/16 (62.5%) | 2/16 (12.5%) | 4/16 (25.0%) | More complex and slower; the original run had a title-expansion retrieval bug and one structured-output refusal. |

## Selected final setting: B-medium

**B-medium is selected for the final system.** It had the best manually reviewed answer quality on the same question set, uses fewer moving parts than C, and does not rely on local embedding-model execution. C's semantic rescoring is real, but it did not outperform B in the measured evaluation. The later Q3 regression fix improves C retrieval but does not retroactively change its original comparison score.

## Cost and latency

Exact token and latency statistics are computed in `REQUIRED_TABLES.md` from the actual provider rows. B uses five 500-word passages; under queue/quota pressure the system switches to smaller A-style retrieval to reduce prompt load, while retaining verification. If the daily provider budget is gone, it makes no provider call and returns cited retrieval-only passages.
