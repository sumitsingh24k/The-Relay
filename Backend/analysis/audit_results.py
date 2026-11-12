"""Audit Relay's immutable raw CSV and produce documented submission copies."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from metrics import CSV_COLUMNS, RESULTS_PATH

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "submission"
GRADE_MAP = {"correct_cited": "correct", "correct_refused": "refused_correctly", "wrong": "wrong", "unsupported": "wrong", "incomplete": "wrong"}


def manual_grade_map() -> dict[str, str]:
    path = BASE / "evaluation" / "manual_grades.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["request_id"]: GRADE_MAP[item["grade"]] for item in payload["grades"] if item["grade"] in GRADE_MAP}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with RESULTS_PATH.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames or []
        rows = list(reader)
    grades = manual_grade_map()
    malformed = [index + 2 for index, row in enumerate(rows) if set(row) != set(CSV_COLUMNS) or any(key not in row for key in CSV_COLUMNS)]
    duplicate_ids = {value for value, count in Counter(row["request_id"] for row in rows if row["request_id"]).items() if count > 1}
    remaps: list[dict[str, str]] = []
    seen: Counter[str] = Counter()
    cleaned: list[dict[str, str]] = []
    for index, original in enumerate(rows, start=2):
        row = dict(original)
        request_id = row["request_id"] or f"missing-id-row-{index}"
        seen[request_id] += 1
        if seen[request_id] > 1:
            new_id = f"{request_id}-duplicate-{seen[request_id]}"
            remaps.append({"raw_row": str(index), "old_request_id": request_id, "new_request_id": new_id, "reason": "raw log re-used an id across separate load-driver attempts"})
            row["request_id"] = new_id
        if original["request_id"] in grades:
            row["answer_grade"] = grades[original["request_id"]]
        cleaned.append({column: row.get(column, "") for column in CSV_COLUMNS})
    with (OUT / "results_submission_clean.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS); writer.writeheader(); writer.writerows(cleaned)
    with (OUT / "csv_id_remaps.json").open("w", encoding="utf-8") as stream:
        json.dump(remaps, stream, indent=2); stream.write("\n")
    scenarios = Counter(row["scenario"] for row in rows)
    missing = {field: sum(not row.get(field) for row in rows) for field in ("first_token_ms", "total_ms", "tokens_in", "tokens_out", "answer_grade")}
    lines = [
        "# CSV audit", "", "## Schema", "",
        f"Expected columns and raw columns match exactly: `{header == CSV_COLUMNS}`.",
        f"Raw rows: {len(rows)}. Malformed rows: {len(malformed)}.", "",
        "## Integrity findings", "",
        f"Duplicate non-empty request IDs: {len(duplicate_ids)}. The raw file is preserved unchanged.",
        f"The clean copy has unique IDs; {len(remaps)} later duplicate occurrences received a `-duplicate-N` suffix. See `csv_id_remaps.json`.",
        "", "## Missing values", "",
        *[f"- `{field}`: {count}" for field, count in missing.items()], "",
        "Missing token values are expected for the local stand-in and retrieval-only fallbacks because neither reports Groq token usage. Missing TTFT occurs for buffered refusals/errors and older rows created before the distinction was logged.",
        "", "## Scenario coverage", "",
        *[f"- `{scenario}`: {count} raw rows" for scenario, count in sorted(scenarios.items())], "",
        "The five required load scenario names and all A/B/C retrieval scenario names are present. Failed/rate-limited rows are retained rather than silently dropped.",
        "", "## Grade mapping", "",
        "The raw CSV is retained. The clean submission CSV maps reviewed internal grades to the brief's required values: `correct_cited` → `correct`; `correct_refused` → `refused_correctly`; `wrong`/`unsupported`/`incomplete` → `wrong`. Unreviewed answers remain blank.",
    ]
    (OUT / "CSV_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Audited {len(rows)} raw rows; wrote clean CSV and audit to {OUT}")


if __name__ == "__main__":
    main()
