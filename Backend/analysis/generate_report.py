"""Generate submission tables and a truthful report draft from recorded raw files."""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.analyze import scenario_tables
from metrics import CSV_COLUMNS, read_rows

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "submission"


def write_csv(name: str, rows: list[dict]) -> None:
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows = read_rows()
    load_names = {"steady", "burst", "sustained_overload", "rpm_halved", "daily_budget_exhausted"}
    load_rows = [row for row in rows if row["scenario"] in load_names]
    write_csv("results_load_only.csv", load_rows)
    tables = scenario_tables(load_rows)
    (OUT / "tables.json").write_text(json.dumps(tables, indent=2) + "\n", encoding="utf-8")
    traces = [json.loads(line) for line in (BASE / "trace.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    slow = sorted((trace for trace in traces if trace.get("timing_ms", {}).get("total") is not None), key=lambda trace: trace["timing_ms"]["total"], reverse=True)[:10]
    (OUT / "slow_request_traces.json").write_text(json.dumps(slow, indent=2) + "\n", encoding="utf-8")
    review_summary: dict[str, dict[str, int]] = {}
    review_path = OUT / "retrieval_review.json"
    if review_path.exists():
        for row in json.loads(review_path.read_text(encoding="utf-8")):
            outcomes = review_summary.setdefault(row["retrieval_setting"], {})
            outcomes[row["grade"]] = outcomes.get(row["grade"], 0) + 1
    (OUT / "retrieval_summary.json").write_text(json.dumps(review_summary, indent=2) + "\n", encoding="utf-8")
    source_counts = Counter((row["scenario"], row["source"], row["status"]) for row in load_rows)
    lines = [
        "# Relay report draft", "", "## Evidence boundary", "",
        "This draft uses only rows actually present in `results.csv`, actual Groq baseline records, and local stand-in traces. Empty answer grades have not been inferred.",
        "", "## Provider calibration", "",
        "See `measurements/groq_baseline.jsonl` and `standin/calibration.json` for the three real Groq calibration calls and the derived stand-in parameters.",
        "", "## Load scenarios", "",
        "| Scenario | Requests | Successful | p50 total ms | p95 total ms | Rate-limit events |", "|---|---:|---:|---:|---:|---:|",
    ]
    for scenario, data in tables.items():
        lines.append(f"| {scenario} | {data['total_requests']} | {data['successful_requests']} | {data['p50_ms'] or 'n/a'} | {data['p95_ms'] or 'n/a'} | {data['rate_limit_events']} |")
    lines += ["", "## Observed source/status counts", "", "```text", *[f"{item}: {count}" for item, count in sorted(source_counts.items())], "```", "", "## Retrieval A/B/C", "", "All 16 questions were sent to each setting with Groq. Detailed answers and citations are stored in `measurements/retrieval_experiments.jsonl`."]
    if review_summary:
        lines += ["", "| Setting | Reviewed outcomes |", "|---|---|"]
        for setting, outcomes in sorted(review_summary.items()):
            lines.append(f"| {setting} | " + ", ".join(f"{grade}: {count}" for grade, count in sorted(outcomes.items())) + " |")
    (OUT / "REPORT_DRAFT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote report evidence to {OUT}")


if __name__ == "__main__":
    main()
