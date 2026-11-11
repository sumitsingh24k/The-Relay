"""Append-only request logging and aggregation for Relay's required CSV schema."""
from __future__ import annotations
import csv
from datetime import UTC, datetime
from pathlib import Path

CSV_COLUMNS = ["request_id","scenario","source","start_time","first_token_ms","total_ms","status","retries","tokens_in","tokens_out","retrieval_setting","answer_grade"]
RESULTS_PATH = Path(__file__).resolve().parent / "results.csv"

def append_result(result: dict, *, scenario: str, source: str, retries: int = 0, answer_grade: str = "") -> None:
    retry_count = result.get("retries", retries)
    row = {"request_id":result.get("request_id",""),"scenario":scenario,"source":source,"start_time":datetime.now(UTC).isoformat(),"first_token_ms":result.get("timing_ms",{}).get("user_visible_ttft") or "","total_ms":result.get("timing_ms",{}).get("total") or "","status":result.get("status","error"),"retries":retry_count,"tokens_in":result.get("usage",{}).get("tokens_in") or "","tokens_out":result.get("usage",{}).get("tokens_out") or "","retrieval_setting":result.get("retrieval_setting","B-medium"),"answer_grade":answer_grade}
    with RESULTS_PATH.open("a", newline="", encoding="utf-8") as f: csv.DictWriter(f,fieldnames=CSV_COLUMNS).writerow(row)

def read_rows() -> list[dict]:
    with RESULTS_PATH.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
