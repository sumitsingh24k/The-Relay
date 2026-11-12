"""Run A/B/C against the same fixed questions and save evidence for manual grading.

`--source groq` produces real cited answers but consumes the account quota.  Grades
remain empty until a person reviews the saved outputs; this script never invents them.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from llm_client import GroqClient, StandInClient
from metrics import append_result
from pipeline import DailyProviderBudgetError, retrieval_only_fallback, run_pipeline
from retrieve import BM25Retriever
from evaluation.evaluate import load_questions

OUT = Path(__file__).resolve().parents[1] / "measurements" / "retrieval_experiments.jsonl"
SETTINGS = ("A-small", "B-medium", "C-medium-expanded")


def completed_keys() -> set[tuple[str, str, int]]:
    if not OUT.exists():
        return set()
    return {
        (row["source"], row["retrieval_setting"], int(row["question_number"]))
        for line in OUT.read_text(encoding="utf-8").splitlines() if line.strip()
        for row in [json.loads(line)]
    }


async def run(source: str, limit: int | None = None, interval_s: float = 0, resume: bool = False) -> None:
    questions = load_questions()[:limit]
    retriever = BM25Retriever()
    OUT.parent.mkdir(exist_ok=True)
    if source == "standin":
        # A standalone retrieval experiment must not inherit the intentionally exhausted
        # daily-budget load-test state.
        import httpx
        async with httpx.AsyncClient() as http:
            (await http.post("http://127.0.0.1:8000/control/reset")).raise_for_status()
            (await http.post("http://127.0.0.1:8000/control/config", json={"rpm": 30, "daily_requests": 500})).raise_for_status()
    done = completed_keys() if resume else set()
    for setting in SETTINGS:
        for index, question in enumerate(questions, start=1):
            if (source, setting, index) in done:
                print(f"{setting} q{index}: already recorded")
                continue
            client = GroqClient() if source == "groq" else StandInClient()
            try:
                result = await run_pipeline(question["q"], client, retriever, setting)
            except DailyProviderBudgetError:
                result = retrieval_only_fallback(question["q"], retriever.retrieve_passages(question["q"], setting), f"retrieval-fallback-{index}")
                result["timing_ms"], result["usage"], result["retries"], result["retrieval_setting"] = ({}, {}, 0, setting)
            except Exception as error:
                result = {"request_id": f"retrieval-error-{setting}-{index}", "status": "error", "answer": "",
                    "citations": [], "claims": [], "refused": True, "verification": {"reason": str(error)},
                    "question": question["q"], "timing_ms": {}, "usage": {}, "retries": 0, "retrieval_setting": setting}
            record = {"recorded_at": datetime.now(UTC).isoformat(), "question_number": index,
                "question_type": question["type"], "expected_paper": question.get("paper"),
                "source": source, "retrieval_setting": setting, "result": result,
                "manual_grade": ""}
            with OUT.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
            append_result(result, scenario=f"retrieval_{setting}", source=source)
            print(f"{setting} q{index}: refused={result['refused']} status={result['status']}")
            if interval_s:
                await asyncio.sleep(interval_s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("groq", "standin"), default="standin")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--interval-s", type=float, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.source, args.limit, args.interval_s, args.resume))
