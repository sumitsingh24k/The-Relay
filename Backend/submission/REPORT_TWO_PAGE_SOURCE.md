# The Relay final report

## 1. What I built and why

Relay is a single-process Python RAG assistant for exactly three verified arXiv papers. It extracts page-aware chunks, retrieves evidence through BM25, uses Groq or a controlled stand-in for structured claims, then checks citation identity and claim-to-evidence support before returning an answer. Verification occurs before the answer reaches the user, so unsupported claims are refused rather than presented as grounded.

## 2. The real service and my stand-in

Eight modest real Groq calls using `openai/gpt-oss-20b` measured model TTFT mean 612.2 ms, p50 678.1 ms and p95 732.1 ms; total latency mean 625.9 ms, p50 689.1 ms and p95 743.0 ms. Mean usage was 91 input and 77 output tokens. Captured headers reported RPD 1000 and TPM 8000. RPM, TPD, concurrent limit, and real-429 recovery were not measured and are not inferred.

The calibrated stand-in uses 639.1 ms base delay, 1.0 ms token delay and a 0.25 load-slowdown multiplier. It can simulate SSE pieces, 503 failure, HTTP 429 with Retry-After, and daily exhaustion. It differs from Groq in answer quality and failure distribution, which are synthetic.

| Table 1 field | Value | Evidence / confidence |
|---|---:|---|
| Real sample | 8 calls | observed JSONL |
| RPD | 1000 | observed header |
| TPM | 8000 | observed header |
| RPM, TPD, concurrency, real 429 recovery | not measured | not forced |

## 3. Results

Repeated local attempts remain retained in raw data. Duration, offered rate, peak queue and cost were not logged per run, so they remain not measured.

| Table 2a scenario | Requests | User TTFT p50/p95/p99 ms | Total p50/p95/p99 ms |
|---|---:|---:|---:|
| Steady | 17 | not measured | 825.8/861.1/861.1 |
| Burst | 25 | not measured | 1433.1/1549.1/1549.1 |
| Sustained overload | 127 | not measured | 963.2/1204.0/1209.5 |
| RPM halved | 26 | 46.6/50.6/50.6 | 808.0/831.9/831.9 |
| Daily budget exhausted | 34 | 37.1/40.4/46.7 | 38.6/1773.3/1780.3 |

| Table 2b scenario | Success % | Rate-limited % | Timeout/error % | Retries/request | Peak queue, tokens/answer, cost/1k |
|---|---:|---:|---:|---:|---|
| Steady | 23.5 | 76.5 | 0.0 | 0.00 | not measured |
| Burst | 40.0 | 60.0 | 0.0 | 0.00 | not measured |
| Sustained overload | 10.2 | 89.8 | 0.0 | 0.00 | not measured |
| RPM halved | 38.5 | 46.2 | 15.4 | 0.00 | not measured |
| Daily budget exhausted | 58.8 | 20.6 | 20.6 | 0.00 | not measured |

## 4. Where the time goes

The slowest historical C-setting stand-in trace took 78,539.0 ms total with 828.0 ms provider model time and no retry. Historic traces lack queue-start and retry timestamps, so waiting, working, and retry decomposition is not retroactively invented. New traces now record queue wait, working time, and retry wait. The observed delay was before verified response delivery, not after the provider's first token.

## 5. When a limit is hit

The scheduler uses bounded queue admission, workers, semaphore concurrency, RPM/TPM/daily limits, and deadlines. Transient 429/5xx responses use at most two retries, Retry-After, exponential backoff and jitter. At daily exhaustion it makes no provider call and returns cited passages with an unavailability message.

## Retrieval quality versus cost

| Table 3 setting | Questions | Correct % | Wrong % | Correct refusal % | Mean tokens | Model TTFT p50/p95 ms | Total p50/p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| A-small | 16 | 62.5 | 12.5 | 25.0 | 1556.2 | 1062.1/1739.9 | 1175.2/2124.4 |
| B-medium | 16 | 68.8 | 6.2 | 25.0 | 2033.6 | 941.8/1233.8 | 1001.8/1522.4 |
| C-medium-expanded | 16 | 62.5 | 12.5 | 25.0 | 1658.0 | 1029.9/1372.6 | 1362.8/11405.9 |

I selected B-medium: on the same 16 questions it achieved 11 correct cited answers, one wrong answer, and four correct refusals. C was a genuine MiniLM bi-encoder experiment, not an assumed improvement.

## How this library will mislead a naive retriever

Generic shared terms can confuse papers: the original query "base Transformer model dimension" retrieved Moshi's 4096 instead of Transformer `d_model = 512`. Latency questions may retrieve several valid values from different Moshi contexts. Short identifiers such as H-Net have weak lexical evidence. Mitigations are distinctive title matching, context-sensitive answers, semantic candidate expansion, and claim-support checks.

## 6. Retries

The controlled stand-in 429 test produced two bounded retries and 2391.264 ms retry wait before a final rate-limited response. This is evidence that retrying a temporary rate limit increases waiting time and provider attempts. Daily quota 429 is treated differently: it switches directly to retrieval-only output because waiting for a day-scale reset would worsen the user experience.

## 7. What the person sees

Users receive a cited verified answer, a safe refusal, or a daily-budget message with retrieved passages. The React UI receives complete verified JSON rather than unverified token streaming; provider-model TTFT is therefore distinct from user-visible response time.

## 8. What I am unsure about, left out, and learned

Eight short real calls do not represent launch-load behavior. I intentionally did not use Redis, microservices, or unverified frontend streaming. I learned that a citation ID can exist while still supporting the wrong claim, and that semantic rescoring can worsen a small corpus.

## Your feedback on Vaani

Teacher AI and Memories stood out because natural-language requirements, prompt review, and retained context reduce setup and repetition. Knowledge versus Memories and readiness-score meaning were less clear. I recommend guided onboarding plus knowledge freshness monitoring, version history, and outdated-answer alerts.

## How I worked with the assistant

I used the assistant to explore concurrent-request architecture, grounded RAG and controlled load testing. I caught the generic-title retrieval bug and chose controlled stand-in stress tests instead of forcing real Groq limits. My contribution was requirement interpretation, architecture direction, evidence checking, debugging, experiment review, and validation.
