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

RPM = int(os.getenv("STANDIN_RPM", "30"))
DAILY_REQUESTS = int(os.getenv("STANDIN_DAILY_REQUESTS", "500"))
BASE_DELAY_MS = float(os.getenv("STANDIN_BASE_DELAY_MS", "250"))
FAILURE_RATE = float(os.getenv("STANDIN_FAILURE_RATE", "0"))
TOKEN_DELAY_MS = float(os.getenv("STANDIN_TOKEN_DELAY_MS", "35"))
state = {"started": time.monotonic(), "requests": 0, "in_flight": 0, "recent": deque()}


def _rate_limited() -> bool:
    now = time.monotonic()
    while state["recent"] and state["recent"][0] <= now - 60:
        state["recent"].popleft()
    return len(state["recent"]) >= RPM


def _message(payload: dict) -> str:
    # A stand-in measures transport behavior; it does not pretend to be a truthful paper-answering model.
    return json.dumps({"answer": "", "claims": [], "refusal": True})


async def completion(request: Request):
    payload = await request.json()
    if state["requests"] >= DAILY_REQUESTS:
        return JSONResponse({"error": {"message": "daily quota exhausted"}}, status_code=429, headers={"Retry-After": "86400"})
    if _rate_limited():
        return JSONResponse({"error": {"message": "rate limit exceeded"}}, status_code=429, headers={"Retry-After": "1"})
    state["requests"] += 1
    state["recent"].append(time.monotonic())
    state["in_flight"] += 1
    try:
        if random.random() < FAILURE_RATE:
            raise HTTPException(503, "configured transient stand-in failure")
        await asyncio.sleep((BASE_DELAY_MS * (1 + 0.25 * max(state["in_flight"] - 1, 0))) / 1000)
        text = _message(payload)
        if not payload.get("stream"):
            return {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 0, "completion_tokens": len(text.split())}}

        async def events():
            for token in text.split(" "):
                yield f"data: {json.dumps({'choices': [{'delta': {'content': token + ' '}}]})}\n\n"
                await asyncio.sleep(TOKEN_DELAY_MS / 1000)
            yield "data: [DONE]\n\n"
        return StreamingResponse(events(), media_type="text/event-stream")
    finally:
        state["in_flight"] -= 1


app = FastAPI(title="Relay stand-in")
app.post("/v1/chat/completions")(completion)
app.get("/health")(lambda: {"status": "ok", "in_flight": state["in_flight"], "requests_today": state["requests"]})
