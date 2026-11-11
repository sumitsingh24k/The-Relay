"""Small async driver. Run only with explicit source/configuration, never fabricates results."""
from __future__ import annotations
import asyncio
import time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from llm_client import StandInClient
from pipeline import run_pipeline
from retrieve import BM25Retriever
from metrics import append_result

SCENARIOS = {
    "steady": {"kind": "steady", "rate_per_min": 12, "duration_s": 60},
    "burst": {"kind": "burst", "rate_per_min": 60, "duration_s": 10},
    "sustained_overload": {"kind": "steady", "rate_per_min": 120, "duration_s": 60},
    "rpm_halved": {"kind": "steady", "rate_per_min": 15, "duration_s": 60},
    "daily_budget_exhausted": {"kind": "burst", "rate_per_min": 60, "duration_s": 10},
}

def arrival_offsets(config: dict) -> list[float]:
    """Deterministic offered-load schedule. The caller must set stand-in caps for halved/budget scenarios."""
    count = max(1, round(config["rate_per_min"] * config["duration_s"] / 60))
    if config["kind"] == "burst": return [0.0] * count
    gap = 60 / config["rate_per_min"]
    return [round(index * gap, 4) for index in range(count)]

async def run_scenario(name:str, questions:list[str], source:str='standin', config:dict|None=None):
    config = config or SCENARIOS[name]
    client=StandInClient() if source=='standin' else None
    if client is None: raise ValueError('Real Groq loads must be explicitly implemented after account measurements.')
    retriever=BM25Retriever()
    offsets = arrival_offsets(config)
    started = time.monotonic()
    async def one(q, offset):
        await asyncio.sleep(max(0, offset - (time.monotonic() - started)))
        try:
            result=await run_pipeline(q,client,retriever)
            append_result(result,scenario=name,source=source)
            return result
        except Exception as error:
            return {'status':'error','error':str(error)}
    offered = [questions[index % len(questions)] for index in range(len(offsets))]
    return await asyncio.gather(*(one(q, offset) for q, offset in zip(offered, offsets)))
