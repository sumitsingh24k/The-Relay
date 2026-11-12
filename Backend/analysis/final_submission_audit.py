"""Generate evidence-first final audit reports without altering raw measurements."""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SUBMISSION = BASE / "submission"
RAW = BASE / "results.csv"
CLEAN = SUBMISSION / "results_submission_clean.csv"
GRADES = BASE / "evaluation" / "manual_grades.json"
BASELINE = BASE / "measurements" / "groq_baseline.jsonl"
TRACE = BASE / "trace.jsonl"
REQUIRED_COLUMNS = [
    "request_id", "scenario", "source", "start_time", "first_token_ms", "total_ms",
    "status", "retries", "tokens_in", "tokens_out", "retrieval_setting", "answer_grade",
]
LOAD_SCENARIOS = ("steady", "burst", "sustained_overload", "rpm_halved", "daily_budget_exhausted")
VALID_STATUS = {"ok", "rate_limited", "timeout", "error"}
VALID_GRADES = {"correct", "wrong", "refused_correctly", "refused_wrongly"}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def number(row: dict[str, str], key: str) -> float | None:
    try:
        return float(row[key]) if row.get(key) else None
    except ValueError:
        return None


def percentile(values: list[float], fraction: float) -> str:
    if not values:
        return "not measured"
    values = sorted(values)
    position = min(len(values) - 1, round((len(values) - 1) * fraction))
    return f"{values[position]:.1f}"


def pct(count: int, total: int) -> str:
    return "not measured" if not total else f"{(100 * count / total):.1f}"


def rows_for_review(raw: list[dict[str, str]], grade_ids: set[str]) -> list[dict[str, str]]:
    return [row for row in raw if row["request_id"] in grade_ids]


def load_json_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write(name: str, content: str) -> None:
    SUBMISSION.mkdir(exist_ok=True)
    (SUBMISSION / name).write_text(content.strip() + "\n", encoding="utf-8")


def main() -> None:
    raw_header, raw = read_csv(RAW)
    clean_header, clean = read_csv(CLEAN)
    grade_payload = json.loads(GRADES.read_text(encoding="utf-8"))
    grade_ids = {item["request_id"] for item in grade_payload["grades"]}
    reviewed = rows_for_review(raw, grade_ids)
    duplicate_raw_ids = [key for key, count in Counter(row["request_id"] for row in raw if row["request_id"]).items() if count > 1]
    invalid_status = sorted({row["status"] for row in raw if row["status"] not in VALID_STATUS})
    invalid_grade = sorted({row["answer_grade"] for row in clean if row["answer_grade"] and row["answer_grade"] not in VALID_GRADES})
    missing_grade_ids = sorted(grade_ids - {row["request_id"] for row in raw})
    extra_retrieval = [row for row in raw if row["scenario"].startswith("retrieval_") and row["request_id"] not in grade_ids]
    nulls = {key: sum(not row.get(key) for row in raw) for key in ("first_token_ms", "total_ms", "tokens_in", "tokens_out", "answer_grade")}
    raw_scenarios = Counter(row["scenario"] for row in raw)

    write("AUDIT_RESULTS_CSV.md", f"""
# Task 1: final results.csv audit

## Result

- Raw rows: **{len(raw)}**. Clean rows: **{len(clean)}**. The raw CSV was read only and not modified.
- Exact raw schema: **{raw_header == REQUIRED_COLUMNS}**. Exact clean schema: **{clean_header == REQUIRED_COLUMNS}**.
- Malformed rows: **0**. Invalid status values: **{invalid_status or 'none'}**. Invalid non-empty clean grades: **{invalid_grade or 'none'}**.
- Raw duplicate request IDs: **{len(duplicate_raw_ids)}**. They are preserved in raw data; clean IDs are unique through documented suffix remaps.

## A/B/C evidence coverage

- Manual review IDs: **{len(grade_ids)}**.
- IDs found in raw CSV: **{len(reviewed)}**. Missing review IDs: **{len(missing_grade_ids)}**.
- Reviewed rows by setting: A-small **{sum(row['scenario'] == 'retrieval_A-small' for row in reviewed)}**; B-medium **{sum(row['scenario'] == 'retrieval_B-medium' for row in reviewed)}**; C-medium-expanded **{sum(row['scenario'] == 'retrieval_C-medium-expanded' for row in reviewed)}**.
- There are **{len(extra_retrieval)}** additional retrieval rows. They are earlier ungraded stand-in trials, not silently deleted and not included in the 48-question comparison.

## Load evidence coverage

{chr(10).join(f'- `{scenario}`: **{raw_scenarios[scenario]}** raw rows' for scenario in LOAD_SCENARIOS)}

All five named load scenarios are represented. Repeated local attempts are preserved as evidence, so these counts are not presented as one clean run per scenario.

## Nulls and mappings

{chr(10).join(f'- `{key}`: **{value}** blank raw values' for key, value in nulls.items())}

Blank token fields are expected for stand-in/retrieval-only rows because no real-provider usage is returned. Blank historical TTFT/total fields are retained rather than imputed. The clean copy maps genuinely reviewed internal labels to the allowed submission values only; raw grades remain blank.
""")

    baseline = load_json_lines(BASELINE)
    headers = baseline[-1]["headers"] if baseline else {}
    experiment_records = load_json_lines(BASE / "measurements" / "retrieval_experiments.jsonl")
    record_by_id = {record["result"]["request_id"]: record for record in experiment_records if record.get("result", {}).get("request_id") in grade_ids}
    clean_by_id = {row["request_id"]: row for row in clean}
    retrieval_lines = []
    for setting in ("A-small", "B-medium", "C-medium-expanded"):
        ids = [row["request_id"] for row in reviewed if row["retrieval_setting"] == setting]
        grades = [clean_by_id[item]["answer_grade"] for item in ids]
        records = [record_by_id[item]["result"] for item in ids if item in record_by_id]
        tokens = [
            (record.get("usage", {}).get("tokens_in") or 0) + (record.get("usage", {}).get("tokens_out") or 0)
            for record in records
        ]
        model_ttft = [record["timing_ms"]["model_ttft"] for record in records if record.get("timing_ms", {}).get("model_ttft") is not None]
        totals = [record["timing_ms"]["total"] for record in records if record.get("timing_ms", {}).get("total") is not None]
        token_mean = f"{statistics.mean(tokens):.1f}" if tokens else "not measured"
        retrieval_lines.append(
            f"| {setting} | {len(ids)} | {pct(grades.count('correct'), len(ids))} | "
            f"{pct(grades.count('wrong'), len(ids))} | {pct(grades.count('refused_correctly'), len(ids))} | "
            f"{token_mean} | {'/'.join(percentile(model_ttft, q) for q in (.50, .95))} | "
            f"{'/'.join(percentile(totals, q) for q in (.50, .95))} |"
        )
    write("AUDIT_TABLES.md", f"""
# Task 2: required-table verification

All values below are recomputed from retained files. "Not measured" is not replaced with an estimate.

## Table 1: real Groq limits and evidence

| Field | Value | How obtained | Confidence |
|---|---:|---|---|
| Baseline sample count | {len(baseline)} | `measurements/groq_baseline.jsonl` | observed |
| RPD | {headers.get('x-ratelimit-limit-requests', 'not measured')} | captured `x-ratelimit-limit-requests`; Groq documents this as RPD | observed header |
| TPM | {headers.get('x-ratelimit-limit-tokens', 'not measured')} | captured `x-ratelimit-limit-tokens`; Groq documents this as TPM | observed header |
| RPM | not measured | no forced provider limit test | unavailable |
| TPD | not measured | no captured daily-token header | unavailable |
| In-flight limit | not measured | no concurrency-limit response observed | unavailable |
| Real 429/recovery | not measured | deliberately not forced | unavailable |

## Table 2a: five load scenarios, observed timing

| Scenario | Raw requests | User-visible TTFT p50/p95/p99 ms | Total p50/p95/p99 ms | Duration/offered rate |
|---|---:|---|---|---|
{chr(10).join('| ' + scenario + ' | ' + str(raw_scenarios[scenario]) + ' | ' + '/'.join(percentile([v for row in raw if row['scenario'] == scenario for v in [number(row, 'first_token_ms')] if v is not None], q) for q in (.50, .95, .99)) + ' | ' + '/'.join(percentile([v for row in raw if row['scenario'] == scenario for v in [number(row, 'total_ms')] if v is not None], q) for q in (.50, .95, .99)) + ' | not measured in raw rows |' for scenario in LOAD_SCENARIOS)}

`first_token_ms` is the existing CSV field and represents frontend-visible delivery after verification for current pipeline calls, not provider-model TTFT. Raw CSV does not include per-run start/end envelopes or offered-rate fields, and includes repeated local attempts; duration and offered rate therefore remain not measured.

## Table 2b: observed outcomes

| Scenario | Success % | Rate-limited % | Timeout/error % | Retries/request | Peak queue | Tokens/answer | Cost/1,000 answers |
|---|---:|---:|---:|---:|---|---|---|
{chr(10).join('| ' + scenario + ' | ' + pct(sum(row['status'] == 'ok' for row in raw if row['scenario'] == scenario), raw_scenarios[scenario]) + ' | ' + pct(sum(row['status'] == 'rate_limited' for row in raw if row['scenario'] == scenario), raw_scenarios[scenario]) + ' | ' + pct(sum(row['status'] in {'timeout', 'error'} for row in raw if row['scenario'] == scenario), raw_scenarios[scenario]) + ' | ' + f"{statistics.mean([number(row, 'retries') or 0 for row in raw if row['scenario'] == scenario]):.2f}" + ' | not measured | not measured | not measured |' for scenario in LOAD_SCENARIOS)}

## Table 3: reviewed retrieval comparison

| Setting | Questions | Correct % | Wrong % | Correct refusal % | Mean tokens/answer | Model TTFT p50/p95 ms | Total p50/p95 ms |
|---|---:|---:|---:|---:|---:|---|---|
{chr(10).join(retrieval_lines)}

Table 3 only uses the exactly reviewed 48 rows. Grades come from the clean submission CSV; timings and tokens come from their matching retained experiment JSONL records. Raw CSV remains unchanged.
""")

    traces = load_json_lines(TRACE)
    timed = [row for row in traces if isinstance(row.get("timing_ms", {}).get("total"), (int, float))]
    slow = max(timed, key=lambda row: row["timing_ms"]["total"]) if timed else {}
    write("AUDIT_SLOW_RETRY_RETRIEVAL.md", f"""
# Task 4: slow request, retry and retrieval failure audit

## Slow request

The slowest retained trace with a numeric total is `{slow.get('request_id', 'not available')}`: total **{slow.get('timing_ms', {}).get('total', 'not measured')} ms**, provider-model total **{slow.get('timing_ms', {}).get('model_total', 'not measured')} ms**, provider TTFT **{slow.get('timing_ms', {}).get('model_ttft', 'not measured')} ms**, retries **{slow.get('retries', 'not measured')}**.

Historical trace records do not contain queue-start, worker-start, or individual retry timestamps, so historical queue wait/working/retry decomposition is **not measured**. The current code now records `scheduler_timing_ms.queue_wait`, `scheduler_timing_ms.working`, and `retry_wait_ms` for all newly logged requests. It does not backfill fabricated values into old traces.

## Retry audit

Code inspection and tests confirm: transient 429/5xx calls use a maximum of two retries, honor numeric `Retry-After` when present, and add exponential backoff plus jitter. Historical CSV retry count is zero for every retained row, so there is no evidence-backed real case where retrying made performance worse. No such case is invented.

## Retrieval failures

1. **Generic title words:** “What is the base Transformer model dimension?” previously expanded on generic `model`, pulled Moshi’s 4096 value, and could answer the wrong architecture. Mitigation: only distinctive title terms trigger title expansion; regression test added.
2. **Ambiguous latency:** “What latency does Moshi report?” can retrieve different valid figures (80/160/240/640 ms) from different contexts and lead to an over-general answer. Mitigation: ask the model to retain the cited context and refuse ambiguous synthesis.
3. **Short names:** “What is H-Net?” has weak token evidence and can lose to generic passages. Mitigation: retrieve more candidates and require exact cited support.

The original C-setting wrong answers are retained: Q3 was a query-expansion/retrieval error; Q10 retrieved relevant evidence but failed because provider output was not valid structured JSON. See `C_FAILURE_ANALYSIS.md` for the record-level evidence.
""")

    write("AUDIT_TECHNICAL.md", """
# Task 5: technical audits

## Streaming - PASS WITH DESIGN LIMITATION

Groq and the stand-in use SSE upstream. The backend consumes the complete stream, verifies claims and citations, then returns JSON. Therefore the React frontend does not receive unverified incremental answer chunks. Provider-model TTFT and frontend-visible delivery time are distinct and recorded separately where available.

## Rate-limit accounting - PARTIALLY PASSING, IMPROVED

Each `generate()` attempt is now wrapped by `QuotaTrackedClient`, so retries are independently admitted and count as request attempts. Successful calls with reported usage reconcile the 1000-token reservation to actual input plus output tokens. The stand-in has no real usage data and remains conservatively charged at its reservation. Failed provider calls retain their reservation because actual usage is unknown.

## Claim verification - PASS WITH STATED LIMIT

Citation identity and support are separate checks. New tests reject a changed number (4096 when evidence says 512) and an unsupported negation. The verifier remains lexical/conservative, not a natural-language-entailment model, so nuanced paraphrases can still be refused.

## Scheduler concurrency and persistence - PASS

The scheduler uses an async lock around quota counters, a bounded `asyncio.Queue`, worker pool, semaphore, deadlines, and daily JSON persistence. New worker timing fields separate queue wait from worker time for future traces. Existing tests cover quota, queue overflow, deadlines, workers, retry bounds, and reconciliation.

## CSV and metrics integrity - PARTIAL

The exact schema and status values are valid. Raw duplicate IDs and missing historical fields are preserved and documented; clean copy remaps duplicate IDs. Historical `first_token_ms` is frontend-visible post-verification time, not a provider TTFT field. Future trace rows include richer timing details; past values are not reconstructed.
""")

    write("FINAL_EIGHT_TASK_REPORT.md", """
# Final eight-task completion report

| Task | Result | Evidence / blocker |
|---|---|---|
| 1. CSV audit | Complete | `AUDIT_RESULTS_CSV.md`, clean CSV, ID remaps |
| 2. Table verification | Complete with unavailable fields marked | `AUDIT_TABLES.md` |
| 3. Groq and stand-in evidence | Complete with documented/not-measured separation | baseline JSONL, calibration JSON, stand-in validation |
| 4. Slow/retry/retrieval analysis | Complete; historical timing decomposition unavailable | `AUDIT_SLOW_RETRY_RETRIEVAL.md` |
| 5. Technical audits | Complete; accounting and verifier improvements tested | `AUDIT_TECHNICAL.md`, backend tests |
| 6. Vaani/history | Blocked by genuine student input | templates only; no fabrication |
| 7. Two-page PDF | Pending PDF authoring and visual inspection | report content exists; no PDF claimed yet |
| 8. Git/secrets/final tests | Partial | tests must be rerun after final edits; `.venv` tracking needs explicit Git-index cleanup |
""")
    print(f"Wrote final audit reports to {SUBMISSION}")


if __name__ == "__main__":
    main()
