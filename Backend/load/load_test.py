"""Run five load shapes through Relay's API and its controllable stand-in.

Start both Uvicorn services first. Every response, including admission failures,
is preserved in the required results.csv schema—nothing is silently discarded.
"""
from __future__ import annotations
import argparse
import asyncio
import sys
import time
from pathlib import Path
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.evaluate import load_questions
from metrics import append_result

API = "http://127.0.0.1:8001"
STANDIN = "http://127.0.0.1:8000"
SCENARIOS = {
    "steady": {"kind": "steady", "rate_per_min": 12, "duration_s": 60, "standin": {"rpm": 30, "daily_requests": 500}},
    "burst": {"kind": "burst", "rate_per_min": 60, "duration_s": 10, "standin": {"rpm": 30, "daily_requests": 500}},
    "sustained_overload": {"kind": "steady", "rate_per_min": 120, "duration_s": 20, "standin": {"rpm": 30, "daily_requests": 500}},
    "rpm_halved": {"kind": "steady", "rate_per_min": 30, "duration_s": 20, "standin": {"rpm": 6, "daily_requests": 500}},
    "daily_budget_exhausted": {"kind": "burst", "rate_per_min": 60, "duration_s": 10, "standin": {"rpm": 30, "daily_requests": 3}},
}

def arrival_offsets(config: dict) -> list[float]:
    count = max(1, round(config["rate_per_min"] * config["duration_s"] / 60))
    if config["kind"] == "burst": return [0.0] * count
    gap = 60 / config["rate_per_min"]
    return [round(index * gap, 4) for index in range(count)]

async def run_scenario(name: str, *, api_url: str = API, duration_scale: float = 1.0) -> list[dict]:
    spec = dict(SCENARIOS[name])
    spec["duration_s"] = max(1, round(spec["duration_s"] * duration_scale, 3))
    offsets, questions = arrival_offsets(spec), [item["q"] for item in load_questions()]
    async with httpx.AsyncClient(timeout=35) as client:
        (await client.post(f"{STANDIN}/control/reset")).raise_for_status()
        (await client.post(f"{STANDIN}/control/config", json=spec["standin"])).raise_for_status()
        started = time.monotonic()
        async def one(index: int, offset: float) -> dict:
            await asyncio.sleep(max(0, offset - (time.monotonic() - started)))
            try:
                response = await client.post(f"{api_url}/chat", json={"question": questions[index % len(questions)], "source": "standin", "retrieval_setting": "B-medium", "scenario": name})
                if response.is_success: return response.json()
                result = {"request_id": f"load-http-{name}-{index}", "status": "rate_limited" if response.status_code == 429 else "error", "timing_ms": {}, "usage": {}, "retrieval_setting": "B-medium", "error": response.text}
            except Exception as error:
                result = {"request_id": f"load-transport-{name}-{index}", "status": "error", "timing_ms": {}, "usage": {}, "retrieval_setting": "B-medium", "error": str(error)}
            append_result(result, scenario=name, source="standin")
            return result
        return await asyncio.gather(*(one(index, offset) for index, offset in enumerate(offsets)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("scenario", choices=[*SCENARIOS, "all"]); parser.add_argument("--api-url", default=API); parser.add_argument("--duration-scale", type=float, default=1.0)
    args = parser.parse_args()
    for name in (list(SCENARIOS) if args.scenario == "all" else [args.scenario]):
        results = asyncio.run(run_scenario(name, api_url=args.api_url, duration_scale=args.duration_scale)); statuses: dict[str, int] = {}
        for result in results: statuses[result.get("status", "error")] = statuses.get(result.get("status", "error"), 0) + 1
        print(f"{name}: {len(results)} offered; {statuses}")
