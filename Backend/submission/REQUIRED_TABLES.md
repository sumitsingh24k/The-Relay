# Submission tables

These tables are computed from recorded raw files. Some scenarios include repeated local attempts; raw rows are retained and no failures are removed. *The raw CSV does not contain a duration or offered-rate field, so those values cannot be reconstructed honestly. Peak queue and costs were also not logged per request.

## Table 2a: observed load latency

| Scenario | Real or stand-in | Requests sent | Duration (s) | Offered rate (per min) | First token p50/p95/p99 (ms) | Total p50/p95/p99 (ms) |
|---|---|---:|---|---|---|---|
| steady | standin | 17 | not measured* | not measured* | not measured/not measured/not measured | 825.8/861.1/861.1 |
| burst | standin | 25 | not measured* | not measured* | not measured/not measured/not measured | 1433.1/1549.1/1549.1 |
| sustained_overload | standin | 127 | not measured* | not measured* | not measured/not measured/not measured | 963.2/1204.0/1209.5 |
| rpm_halved | retrieval_only, standin | 26 | not measured* | not measured* | 46.6/50.6/50.6 | 808.0/831.9/831.9 |
| daily_budget_exhausted | retrieval_only, standin | 34 | not measured* | not measured* | 37.1/40.4/46.7 | 38.6/1773.3/1780.3 |

## Table 2b: observed load outcomes

| Scenario | Succeeded % | Rate-limited % | Timed out/given up % | Retries/request | Peak queue length | Tokens/answer | Cost/1,000 answers |
|---|---:|---:|---:|---:|---:|---:|---:|
| steady | 23.5 | 76.5 | 0.0 | 0.00 | not measured | not measured | not measured |
| burst | 40.0 | 60.0 | 0.0 | 0.00 | not measured | not measured | not measured |
| sustained_overload | 10.2 | 89.8 | 0.0 | 0.00 | not measured | not measured | not measured |
| rpm_halved | 38.5 | 46.2 | 15.4 | 0.00 | not measured | not measured | not measured |
| daily_budget_exhausted | 58.8 | 20.6 | 20.6 | 0.00 | not measured | not measured | not measured |

## Table 3: retrieval settings

| Setting | Questions | Correct cited % | Wrong % | Correctly refused % | Tokens/answer | Model TTFT p50/p95 (ms) | Total p50/p95 (ms) |
|---|---:|---:|---:|---:|---:|---|---|
| A-small | 16 | 62.5 | 12.5 | 25.0 | 1556.2 | 1062.1/1739.9 | 1175.2/2124.4 |
| B-medium | 16 | 68.8 | 6.2 | 25.0 | 2033.6 | 941.8/1233.8 | 1001.8/1522.4 |
| C-medium-expanded | 16 | 62.5 | 12.5 | 25.0 | 1658.0 | 1029.9/1372.6 | 1362.8/11405.9 |
