"""Compute UI/report metrics only from actual rows in results.csv."""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from metrics import read_rows

def number(row,key):
    try:return float(row[key])
    except (ValueError,TypeError):return None

def summarize(rows=None):
    rows=read_rows() if rows is None else rows
    times=[number(r,'total_ms') for r in rows if number(r,'total_ms') is not None]
    ttft=[number(r,'first_token_ms') for r in rows if number(r,'first_token_ms') is not None]
    def pct(xs,p):
        if not xs:return None
        xs=sorted(xs);return round(xs[min(len(xs)-1,round((len(xs)-1)*p))],2)
    statuses={}
    for row in rows: statuses[row['status']]=statuses.get(row['status'],0)+1
    return {"total_requests":len(rows),"successful_requests":statuses.get('ok',0),"failed_requests":len(rows)-statuses.get('ok',0),"average_response_ms":round(sum(times)/len(times),2) if times else None,"p50_ms":pct(times,.5),"p95_ms":pct(times,.95),"p99_ms":pct(times,.99) if len(times)>=100 else None,"ttft_p50_ms":pct(ttft,.5),"retry_count":sum(int(r['retries'] or 0) for r in rows),"rate_limit_events":statuses.get('rate_limited',0),"queue_length":None,"status_distribution":statuses}

def scenario_tables(rows=None):
    """Raw CSV -> required table 2 style aggregates. Missing data stays None, never fabricated."""
    rows = read_rows() if rows is None else rows
    output = {}
    for scenario in sorted({row["scenario"] for row in rows}):
        group = [row for row in rows if row["scenario"] == scenario]
        output[scenario] = summarize(group)
    return output
