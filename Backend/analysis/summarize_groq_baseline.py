"""Summarize only recorded real Groq baseline measurements."""
from __future__ import annotations
import json
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "measurements" / "groq_baseline.jsonl"
OUT = BASE / "submission" / "GROQ_BASELINE_SUMMARY.md"


def pct(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    return round(values[min(len(values) - 1, round((len(values) - 1) * fraction))], 3)


def main() -> None:
    records = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    ok = [row for row in records if row.get("status") == "ok"]
    totals = [float(row["total_ms"]) for row in ok if row.get("total_ms") is not None]
    ttft = [float(row["model_ttft_ms"]) for row in ok if row.get("model_ttft_ms") is not None]
    tokens_in = [int(row["tokens_in"]) for row in ok if row.get("tokens_in") is not None]
    tokens_out = [int(row["tokens_out"]) for row in ok if row.get("tokens_out") is not None]
    header_keys = sorted({key for row in records for key in row.get("headers", {})})
    lines = [
        "# Real Groq baseline summary", "",
        f"Recorded calls: {len(records)}. Successful calls: {len(ok)}.",
        "", "| Metric | Measured value |", "|---|---:|",
        f"| Model TTFT mean (ms) | {round(statistics.mean(ttft), 3) if ttft else 'not measured'} |",
        f"| Model TTFT p50 (ms) | {pct(ttft, .5) if ttft else 'not measured'} |",
        f"| Model TTFT p95 (ms) | {pct(ttft, .95) if ttft else 'not measured'} |",
        f"| Total latency mean (ms) | {round(statistics.mean(totals), 3) if totals else 'not measured'} |",
        f"| Total latency p50 (ms) | {pct(totals, .5) if totals else 'not measured'} |",
        f"| Total latency p95 (ms) | {pct(totals, .95) if totals else 'not measured'} |",
        f"| Mean input tokens | {round(statistics.mean(tokens_in), 3) if tokens_in else 'not measured'} |",
        f"| Mean output tokens | {round(statistics.mean(tokens_out), 3) if tokens_out else 'not measured'} |",
        "", "## Returned provider headers", "", *(f"- `{key}`" for key in header_keys),
        "", "Only recorded headers are reported. Exact account RPM/TPD and a real 429 recovery were not measured in this modest baseline and must not be inferred from this file.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Summarized {len(records)} measurement rows")


if __name__ == "__main__":
    main()
