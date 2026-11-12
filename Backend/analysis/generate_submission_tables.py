"""Create brief-compatible tables from recorded rows only; unknown values stay not measured."""
from __future__ import annotations
import json
import statistics
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from metrics import read_rows

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "submission"
LOADS = ("steady", "burst", "sustained_overload", "rpm_halved", "daily_budget_exhausted")


def values(rows: list[dict], key: str) -> list[float]:
    output = []
    for row in rows:
        try:
            output.append(float(row[key]))
        except (KeyError, TypeError, ValueError):
            pass
    return output


def p(values_: list[float], q: float) -> str:
    if not values_:
        return "not measured"
    ordered = sorted(values_)
    return f"{ordered[min(len(ordered) - 1, round((len(ordered) - 1) * q))]:.1f}"


def load_tables(rows: list[dict]) -> list[str]:
    lines = ["## Table 2a: observed load latency", "", "| Scenario | Real or stand-in | Requests sent | Duration (s) | Offered rate (per min) | First token p50/p95/p99 (ms) | Total p50/p95/p99 (ms) |", "|---|---|---:|---|---|---|---|"]
    lines2 = ["", "## Table 2b: observed load outcomes", "", "| Scenario | Succeeded % | Rate-limited % | Timed out/given up % | Retries/request | Peak queue length | Tokens/answer | Cost/1,000 answers |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name in LOADS:
        group = [row for row in rows if row["scenario"] == name]
        count = len(group)
        sources = ", ".join(sorted(set(row["source"] for row in group))) or "not measured"
        first, total = values(group, "first_token_ms"), values(group, "total_ms")
        lines.append(f"| {name} | {sources} | {count} | not measured* | not measured* | {p(first,.5)}/{p(first,.95)}/{p(first,.99)} | {p(total,.5)}/{p(total,.95)}/{p(total,.99)} |")
        statuses = Counter(row["status"] for row in group)
        success = 100 * statuses["ok"] / count if count else 0
        rate = 100 * statuses["rate_limited"] / count if count else 0
        errors = 100 * (count - statuses["ok"] - statuses["rate_limited"]) / count if count else 0
        retries = statistics.mean(values(group, "retries")) if values(group, "retries") else 0
        token_counts = [a + b for a, b in zip(values(group, "tokens_in"), values(group, "tokens_out"))]
        token_mean = f"{statistics.mean(token_counts):.1f}" if token_counts else "not measured"
        lines2.append(f"| {name} | {success:.1f} | {rate:.1f} | {errors:.1f} | {retries:.2f} | not measured | {token_mean} | not measured |")
    return lines + lines2


def retrieval_table() -> list[str]:
    review = json.loads((OUT / "retrieval_review.json").read_text(encoding="utf-8"))
    experiments = [json.loads(line) for line in (BASE / "measurements" / "retrieval_experiments.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {row["result"]["request_id"]: row["result"] for row in experiments}
    lines = ["", "## Table 3: retrieval settings", "", "| Setting | Questions | Correct cited % | Wrong % | Correctly refused % | Tokens/answer | Model TTFT p50/p95 (ms) | Total p50/p95 (ms) |", "|---|---:|---:|---:|---:|---:|---|---|"]
    for setting in ("A-small", "B-medium", "C-medium-expanded"):
        group = [row for row in review if row["retrieval_setting"] == setting]
        grades = Counter(row["grade"] for row in group)
        result_rows = [by_id[row["request_id"]] for row in group if row["request_id"] in by_id]
        tokens = [result["usage"].get("tokens_in", 0) + result["usage"].get("tokens_out", 0) for result in result_rows if result.get("usage", {}).get("tokens_in") is not None and result.get("usage", {}).get("tokens_out") is not None]
        ttft = [result["timing_ms"].get("model_ttft") for result in result_rows if result.get("timing_ms", {}).get("model_ttft") is not None]
        totals = [result["timing_ms"].get("total") for result in result_rows if result.get("timing_ms", {}).get("total") is not None]
        n = len(group)
        lines.append(f"| {setting} | {n} | {100 * grades['correct_cited']/n:.1f} | {100 * grades['wrong']/n:.1f} | {100 * grades['correct_refused']/n:.1f} | {statistics.mean(tokens):.1f} | {p(ttft,.5)}/{p(ttft,.95)} | {p(totals,.5)}/{p(totals,.95)} |")
    return lines


def main() -> None:
    lines = ["# Submission tables", "", "These tables are computed from recorded raw files. Some scenarios include repeated local attempts; raw rows are retained and no failures are removed. *The raw CSV does not contain a duration or offered-rate field, so those values cannot be reconstructed honestly. Peak queue and costs were also not logged per request.", ""]
    lines.extend(load_tables(read_rows()))
    lines.extend(retrieval_table())
    (OUT / "REQUIRED_TABLES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote required table draft")


if __name__ == "__main__":
    main()
