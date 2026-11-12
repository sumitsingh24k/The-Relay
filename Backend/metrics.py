"""Append-only request logging and aggregation for Relay's required CSV schema."""
from __future__ import annotations
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

CSV_COLUMNS = ["request_id","scenario","source","start_time","first_token_ms","total_ms","status","retries","tokens_in","tokens_out","retrieval_setting","answer_grade"]
RESULTS_PATH = Path(__file__).resolve().parent / "results.csv"
TRACE_PATH = Path(__file__).resolve().parent / "trace.jsonl"

def append_result(result: dict, *, scenario: str, source: str, retries: int = 0, answer_grade: str = "") -> None:
    retry_count = result.get("retries", retries)
    row = {"request_id":result.get("request_id",""),"scenario":scenario,"source":source,"start_time":datetime.now(UTC).isoformat(),"first_token_ms":result.get("timing_ms",{}).get("user_visible_ttft") or "","total_ms":result.get("timing_ms",{}).get("total") or "","status":result.get("status","error"),"retries":retry_count,"tokens_in":result.get("usage",{}).get("tokens_in") or "","tokens_out":result.get("usage",{}).get("tokens_out") or "","retrieval_setting":result.get("retrieval_setting","B-medium"),"answer_grade":answer_grade}
    with RESULTS_PATH.open("a", newline="", encoding="utf-8") as f: csv.DictWriter(f,fieldnames=CSV_COLUMNS).writerow(row)
    trace = {
        "logged_at": row["start_time"], "request_id": row["request_id"], "scenario": scenario,
        "source": source, "status": row["status"], "retries": row["retries"],
        "timing_ms": result.get("timing_ms", {}), "usage": result.get("usage", {}),
        "retrieval_setting": row["retrieval_setting"], "retrieval_attempts": result.get("retrieval_attempts"),
        "scheduler_timing_ms": result.get("scheduler_timing_ms"), "retry_wait_ms": result.get("retry_wait_ms", 0),
        "verification": result.get("verification"), "fallback": result.get("fallback"),
    }
    with TRACE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace) + "\n")

def read_rows() -> list[dict]:
    with RESULTS_PATH.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
