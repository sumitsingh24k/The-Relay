# The Relay - final report

## 1. What I built and why

Relay is a single-process Python RAG assistant for exactly three verified arXiv papers. It extracts page-aware chunks, retrieves evidence, asks Groq for structured claims, then checks both citation identity and claim-to-evidence support before returning an answer. The design decision that shaped the system was **verification before exposure**: an answer can be slower, but it must not be presented as grounded unless the cited passages support it.

## 2. The real service and my stand-in

I recorded eight modest real Groq calibration calls using `openai/gpt-oss-20b`: model-TTFT mean 612.2 ms, p50 678.1 ms, p95 732.1 ms; total-latency mean 625.9 ms, p50 689.1 ms, p95 743.0 ms. Each calibration response used 91 input and 77 output tokens. Returned headers reported an RPD value of 1000 and TPM value of 8000 for this active model. RPM, TPD, concurrent limit, and real-429 recovery were not measured, so I do not claim them.

The stand-in loads a calibration derived from those measurements: 639.1 ms base delay, 1.0 ms estimated token delay, 0.25 load-slowdown multiplier, configurable 503 failure, daily quota, and 429 plus Retry-After. I validated SSE pieces, 429/Retry-After, and 503 locally. It differs most from Groq because its generation quality and failure distribution are synthetic.

## 3. Results

Five stand-in scenarios were retained as raw rows. Repeated local attempts remain in the raw data, so duration/offered rate/peak queue cannot be reconstructed and are marked not measured.

| Scenario | Requests | Total p50/p95 ms | Success % | Rate-limited % |
|---|---:|---:|---:|---:|
| Steady | 17 | 825.8 / 861.1 | 23.5 | 76.5 |
| Burst | 25 | 1433.1 / 1549.1 | 40.0 | 60.0 |
| Sustained overload | 127 | 963.2 / 1204.0 | 10.2 | 89.8 |
| RPM halved | 26 | 808.0 / 831.9 | 38.5 | 46.2 |
| Daily budget exhausted | 34 | 38.6 / 1773.3 | 58.8 | 20.6 |

All figures and missing-data notes are reproducible from `results.csv`, `results_submission_clean.csv`, and `REQUIRED_TABLES.md`.

## 4. Where the time goes

The slowest trace was a C-setting stand-in request: 78,539.0 ms total while provider model work was 828.0 ms and retry count was zero. A slow Groq C run took 37,520.6 ms total while model work was 1,318.7 ms and provider TTFT was 1,029.9 ms. Therefore most observed delay occurred before verified response delivery, not after the provider's first token. Existing historical traces do not split queue, retrieval/model-load, and verification timestamps separately; that is a measurement limitation, not an invented attribution.

## 5. When a limit is hit

The scheduler admits work only within RPM, TPM, daily budget, queue capacity, concurrency, and deadline limits. Queue-full and expired requests are rejected. Per-minute 429/5xx responses use bounded exponential backoff with jitter and honor Retry-After. Under pressure it uses smaller retrieval while keeping safety verification. At daily exhaustion it makes **no provider call** and sends cited retrieved passages with an unavailability explanation.

## Retrieval: quality versus cost

| Setting | Correct cited % | Wrong % | Correctly refused % | Tokens/answer | TTFT p50/p95 ms |
|---|---:|---:|---:|---:|---|
| A: 225 words, top 3 | 62.5 | 12.5 | 25.0 | 1556.2 | 1062.1 / 1739.9 |
| B: 500 words, top 5 | 68.8 | 6.2 | 25.0 | 2033.6 | 941.8 / 1233.8 |
| C: 500 words, BM25 8 then MiniLM 4 | 62.5 | 12.5 | 25.0 | 1658.0 | 1029.9 / 1372.6 |

I select **B-medium**. It was best on the same 16-question review: 11 correct cited, one wrong, and four correct refusals. C was a real bi-encoder experiment, not a claimed win. Its original score included a generic-title expansion bug and a structured-output refusal; the retrieval bug was fixed and regression-tested, but I did not rewrite its original result.

## How this library will mislead a naive retriever

1. Shared generic words cause paper confusion: "base Transformer model dimension" originally pulled Moshi through `model`.
2. Ambiguous latency questions have several valid numbers: "What latency does Moshi report?" can retrieve 80, 160, 240, or 640 ms in different contexts.
3. Short names are weak queries: "What is H-Net?" has only `h`/`net`, making formatting and ranking fragile.

## 6. Retries

Retries are limited to two transient 429/5xx failures, use Retry-After when supplied, then exponential backoff plus jitter. Retrying a daily-quota 429 would only delay the user (the stand-in returns Retry-After 86400), so it is classified as daily exhaustion and switched to retrieval-only output.

## 7. What the person sees

At 3pm daily budget exhaustion, the user receives an explicit message that the daily model budget is exhausted plus up to three cited retrieved passages. They do not receive an unverified synthesis.

## 8. What I am unsure about, left out, and learned

My least certain assumption is that eight short real calibration calls represent provider behavior under launch load; they do not. I deliberately did not add Redis/microservices or unverified frontend token streaming. I learned that citation existence and citation support are different checks, and that semantic rescoring can still worsen a small-paper corpus.

## Your feedback on Vaani

The student explored Vaani and found Teacher AI and Memories especially useful: natural-language agent requirements, reviewable prompt changes, and retained call context reduce manual configuration and repeated customer information. Knowledge versus Memories and the Teacher AI readiness score were less clear. The suggested improvement is guided onboarding plus knowledge freshness/accuracy monitoring with version history and outdated-answer alerts.

## How I worked with the assistant

The student used the assistant to explore concurrent-request architecture, evidence-grounded RAG, and failure/load testing. The student caught a retrieval bug in which a generic `model` title match pulled Moshi's 4096 dimension for a Transformer question; the bug was fixed and regression-tested. The student also chose not to force real Groq rate limits, using modest real measurements and controlled stand-in failure tests instead. The complete student reflection is retained in `CONVERSATION_HISTORY_CHECKLIST.md`.
