"""Local OpenAI-compatible stand-in with explicit failure and quota controls."""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

CALIBRATION_PATH = os.path.join(os.path.dirname(__file__), "calibration.json")
try:
    with open(CALIBRATION_PATH, encoding="utf-8") as calibration_file:
        calibrated = json.load(calibration_file).get("standin", {})
except FileNotFoundError:
    calibrated = {}
config = {
    "rpm": int(os.getenv("STANDIN_RPM", "30")),
    "daily_requests": int(os.getenv("STANDIN_DAILY_REQUESTS", "500")),
    "base_delay_ms": float(os.getenv("STANDIN_BASE_DELAY_MS", str(calibrated.get("base_delay_ms", 250)))),
    "failure_rate": float(os.getenv("STANDIN_FAILURE_RATE", str(calibrated.get("failure_rate", 0)))),
    "token_delay_ms": float(os.getenv("STANDIN_TOKEN_DELAY_MS", str(calibrated.get("token_delay_ms", 35)))),
    "load_slowdown_factor": float(calibrated.get("load_slowdown_factor", 0.25)),
}
state = {"started": time.monotonic(), "requests": 0, "in_flight": 0, "recent": deque()}


class ControlConfig(BaseModel):
    rpm: int | None = None
    daily_requests: int | None = None
    base_delay_ms: float | None = None
    failure_rate: float | None = None
    token_delay_ms: float | None = None
    load_slowdown_factor: float | None = None


def _rate_limited() -> bool:
    now = time.monotonic()
    while state["recent"] and state["recent"][0] <= now - 60:
        state["recent"].popleft()
    return len(state["recent"]) >= config["rpm"]


def _message(payload: dict) -> str:
    # A stand-in measures transport behavior; it does not pretend to be a truthful paper-answering model.
    return json.dumps({"answer": "", "claims": [], "refusal": True})


async def completion(request: Request):
    payload = await request.json()
    if state["requests"] >= config["daily_requests"]:
        return JSONResponse({"error": {"message": "daily quota exhausted"}}, status_code=429, headers={"Retry-After": "86400"})
    if _rate_limited():
        return JSONResponse({"error": {"message": "rate limit exceeded"}}, status_code=429, headers={"Retry-After": "1"})
    state["requests"] += 1
    state["recent"].append(time.monotonic())
    state["in_flight"] += 1
    try:
        if random.random() < config["failure_rate"]:
            raise HTTPException(503, "configured transient stand-in failure")
        await asyncio.sleep((config["base_delay_ms"] * (1 + config["load_slowdown_factor"] * max(state["in_flight"] - 1, 0))) / 1000)
        text = _message(payload)
        if not payload.get("stream"):
            return {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 0, "completion_tokens": len(text.split())}}

        async def events():
            for token in text.split(" "):
                yield f"data: {json.dumps({'choices': [{'delta': {'content': token + ' '}}]})}\n\n"
                await asyncio.sleep(config["token_delay_ms"] / 1000)
            yield f"data: {json.dumps({'choices': [], 'usage': {'prompt_tokens': 0, 'completion_tokens': len(text.split())}})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(events(), media_type="text/event-stream")
    finally:
        state["in_flight"] -= 1


app = FastAPI(title="Relay stand-in")
app.post("/v1/chat/completions")(completion)
app.get("/health")(lambda: {"status": "ok", "in_flight": state["in_flight"], "requests_today": state["requests"], "config": config})

@app.post("/control/reset")
async def reset():
    state["requests"] = 0
    state["recent"].clear()
    return {"status": "reset", "config": config}

@app.post("/control/config")
async def configure(update: ControlConfig):
    for key, value in update.model_dump(exclude_none=True).items():
        if key in {"rpm", "daily_requests"} and value < 1:
            raise HTTPException(400, f"{key} must be at least one")
        if key in {"base_delay_ms", "token_delay_ms", "failure_rate", "load_slowdown_factor"} and value < 0:
            raise HTTPException(400, f"{key} cannot be negative")
        config[key] = value
    return {"status": "configured", "config": config}
