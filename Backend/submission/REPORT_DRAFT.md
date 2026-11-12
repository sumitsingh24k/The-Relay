# Relay report draft

## Evidence boundary

This draft uses only rows actually present in `results.csv`, actual Groq baseline records, and local stand-in traces. Empty answer grades have not been inferred.

## Provider calibration

See `measurements/groq_baseline.jsonl` and `standin/calibration.json` for the three real Groq calibration calls and the derived stand-in parameters.

## Load scenarios

| Scenario | Requests | Successful | p50 total ms | p95 total ms | Rate-limit events |
|---|---:|---:|---:|---:|---:|
| burst | 25 | 10 | 1433.13 | 1549.11 | 15 |
| daily_budget_exhausted | 34 | 20 | 38.59 | 1773.33 | 7 |
| rpm_halved | 26 | 10 | 807.97 | 831.94 | 12 |
| steady | 17 | 4 | 825.81 | 861.11 | 13 |
| sustained_overload | 127 | 13 | 963.24 | 1204.02 | 114 |

## Observed source/status counts

```text
('burst', 'standin', 'ok'): 10
('burst', 'standin', 'rate_limited'): 15
('daily_budget_exhausted', 'retrieval_only', 'ok'): 14
('daily_budget_exhausted', 'standin', 'error'): 7
('daily_budget_exhausted', 'standin', 'ok'): 6
('daily_budget_exhausted', 'standin', 'rate_limited'): 7
('rpm_halved', 'retrieval_only', 'ok'): 4
('rpm_halved', 'standin', 'error'): 4
('rpm_halved', 'standin', 'ok'): 6
('rpm_halved', 'standin', 'rate_limited'): 12
('steady', 'standin', 'ok'): 4
('steady', 'standin', 'rate_limited'): 13
('sustained_overload', 'standin', 'ok'): 13
('sustained_overload', 'standin', 'rate_limited'): 114
```

## Retrieval A/B/C

All 16 questions were sent to each setting with Groq. Detailed answers and citations are stored in `measurements/retrieval_experiments.jsonl`.

| Setting | Reviewed outcomes |
|---|---|
| A-small | correct_cited: 10, correct_refused: 4, wrong: 2 |
| B-medium | correct_cited: 11, correct_refused: 4, wrong: 1 |
| C-medium-expanded | correct_cited: 10, correct_refused: 4, wrong: 2 |
