"""Apply only explicitly supplied manual grades to results.csv-derived evidence.

This tool never chooses a grade.  Populate manual_grades.json with request_id and
grade after opening the matching retrieval_experiments.jsonl response.
"""
from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
EXPERIMENTS = BASE.parent / "measurements" / "retrieval_experiments.jsonl"
GRADES = BASE / "manual_grades.json"
OUT = BASE.parent / "submission" / "retrieval_review.json"


def main() -> None:
    supplied = {entry["request_id"]: entry for entry in json.loads(GRADES.read_text(encoding="utf-8"))["grades"]}
    # Earlier calibration/proof runs may duplicate a question-setting pair.  Retain
    # the latest actual result so the comparison is exactly 16 questions x 3 settings.
    latest: dict[tuple[str, str, int], dict] = {}
    for line in EXPERIMENTS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["source"] == "groq":
                latest[(row["source"], row["retrieval_setting"], int(row["question_number"]))] = row
    rows = list(latest.values())
    reviewed = []
    for row in rows:
        result = row["result"]
        reviewer_entry = supplied.get(result["request_id"], {})
        reviewed.append({
            "request_id": result["request_id"], "question_number": row["question_number"],
            "retrieval_setting": row["retrieval_setting"], "source": row["source"],
            "question": result.get("question", ""), "expected_paper": row.get("expected_paper"),
            "grade": reviewer_entry.get("grade", "not_reviewed"),
            "reviewer_explanation": reviewer_entry.get("review_note", "No manual review entered."),
            "answer": result.get("answer", ""), "citations": result.get("citations", []),
        })
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(reviewed, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(reviewed)} review rows; {sum(row['grade'] != 'not_reviewed' for row in reviewed)} manually graded.")


if __name__ == "__main__":
    main()
