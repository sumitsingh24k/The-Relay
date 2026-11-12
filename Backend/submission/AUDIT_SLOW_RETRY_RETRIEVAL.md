# Task 4: slow request, retry and retrieval failure audit

## Slow request

The slowest retained trace with a numeric total is `req-2e09ac62b89e`: total **78538.968 ms**, provider-model total **828.019 ms**, provider TTFT **825.864 ms**, retries **0**.

Historical trace records do not contain queue-start, worker-start, or individual retry timestamps, so historical queue wait/working/retry decomposition is **not measured**. The current code now records `scheduler_timing_ms.queue_wait`, `scheduler_timing_ms.working`, and `retry_wait_ms` for all newly logged requests. It does not backfill fabricated values into old traces.

## Retry audit

Code inspection and tests confirm: transient 429/5xx calls use a maximum of two retries, honor numeric `Retry-After` when present, and add exponential backoff plus jitter. Historical CSV retry count is zero for every retained row, so there is no evidence-backed real case where retrying made performance worse. No such case is invented.

## Retrieval failures

1. **Generic title words:** “What is the base Transformer model dimension?” previously expanded on generic `model`, pulled Moshi’s 4096 value, and could answer the wrong architecture. Mitigation: only distinctive title terms trigger title expansion; regression test added.
2. **Ambiguous latency:** “What latency does Moshi report?” can retrieve different valid figures (80/160/240/640 ms) from different contexts and lead to an over-general answer. Mitigation: ask the model to retain the cited context and refuse ambiguous synthesis.
3. **Short names:** “What is H-Net?” has weak token evidence and can lose to generic passages. Mitigation: retrieve more candidates and require exact cited support.

The original C-setting wrong answers are retained: Q3 was a query-expansion/retrieval error; Q10 retrieved relevant evidence but failed because provider output was not valid structured JSON. See `C_FAILURE_ANALYSIS.md` for the record-level evidence.
