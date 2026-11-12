# Task 2: required-table verification

All values below are recomputed from retained files. "Not measured" is not replaced with an estimate.

## Table 1: real Groq limits and evidence

| Field | Value | How obtained | Confidence |
|---|---:|---|---|
| Baseline sample count | 8 | `measurements/groq_baseline.jsonl` | observed |
| RPD | 1000 | captured `x-ratelimit-limit-requests`; Groq documents this as RPD | observed header |
| TPM | 8000 | captured `x-ratelimit-limit-tokens`; Groq documents this as TPM | observed header |
| RPM | not measured | no forced provider limit test | unavailable |
| TPD | not measured | no captured daily-token header | unavailable |
| In-flight limit | not measured | no concurrency-limit response observed | unavailable |
| Real 429/recovery | not measured | deliberately not forced | unavailable |

## Table 2a: five load scenarios, observed timing

| Scenario | Raw requests | User-visible TTFT p50/p95/p99 ms | Total p50/p95/p99 ms | Duration/offered rate |
|---|---:|---|---|---|
| steady | 17 | not measured/not measured/not measured | 825.8/861.1/861.1 | not measured in raw rows |
| burst | 25 | not measured/not measured/not measured | 1433.1/1549.1/1549.1 | not measured in raw rows |
| sustained_overload | 127 | not measured/not measured/not measured | 963.2/1204.0/1209.5 | not measured in raw rows |
| rpm_halved | 26 | 46.6/50.6/50.6 | 808.0/831.9/831.9 | not measured in raw rows |
| daily_budget_exhausted | 34 | 37.1/40.4/46.7 | 38.6/1773.3/1780.3 | not measured in raw rows |

`first_token_ms` is the existing CSV field and represents frontend-visible delivery after verification for current pipeline calls, not provider-model TTFT. Raw CSV does not include per-run start/end envelopes or offered-rate fields, and includes repeated local attempts; duration and offered rate therefore remain not measured.

## Table 2b: observed outcomes

| Scenario | Success % | Rate-limited % | Timeout/error % | Retries/request | Peak queue | Tokens/answer | Cost/1,000 answers |
|---|---:|---:|---:|---:|---|---|---|
| steady | 23.5 | 76.5 | 0.0 | 0.00 | not measured | not measured | not measured |
| burst | 40.0 | 60.0 | 0.0 | 0.00 | not measured | not measured | not measured |
| sustained_overload | 10.2 | 89.8 | 0.0 | 0.00 | not measured | not measured | not measured |
| rpm_halved | 38.5 | 46.2 | 15.4 | 0.00 | not measured | not measured | not measured |
| daily_budget_exhausted | 58.8 | 20.6 | 20.6 | 0.00 | not measured | not measured | not measured |

## Table 3: reviewed retrieval comparison

| Setting | Questions | Correct % | Wrong % | Correct refusal % | Mean tokens/answer | Model TTFT p50/p95 ms | Total p50/p95 ms |
|---|---:|---:|---:|---:|---:|---|---|
| A-small | 16 | 62.5 | 12.5 | 25.0 | 1556.2 | 1062.1/1739.9 | 1175.2/2124.4 |
| B-medium | 16 | 68.8 | 6.2 | 25.0 | 2033.6 | 941.8/1233.8 | 1001.8/1522.4 |
| C-medium-expanded | 16 | 62.5 | 12.5 | 25.0 | 1658.0 | 1029.9/1372.6 | 1362.8/11405.9 |

Table 3 only uses the exactly reviewed 48 rows. Grades come from the clean submission CSV; timings and tokens come from their matching retained experiment JSONL records. Raw CSV remains unchanged.
