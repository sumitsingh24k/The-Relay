"""Run small, auditable real-Groq baseline measurements without fabricating limits.

Usage: ..\\.venv\\Scripts\\python.exe measure_groq.py --calls 3
The script never prints the API key.  It persists exact returned rate-limit headers
and measured timings under measurements/ for the report and stand-in calibration.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from llm_client import GroqClient, ProviderError
from metrics import append_result

MEASUREMENTS = Path(__file__).with_name("measurements") / "groq_baseline.jsonl"
RATE_HEADERS = (
    "retry-after", "x-ratelimit-limit-requests", "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-requests", "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens", "x-request-id",
)


def selected_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in headers.items() if key.lower() in RATE_HEADERS}


async def measure(calls: int, interval_s: float = 0) -> list[dict]:
    client = GroqClient()
    MEASUREMENTS.parent.mkdir(exist_ok=True)
    rows: list[dict] = []
    messages = [
        {"role": "system", "content": "Reply with exactly one short sentence."},
        {"role": "user", "content": "Say that this is a Relay provider calibration request."},
    ]
    for index in range(calls):
        recorded_at = datetime.now(UTC).isoformat()
        request_id = f"groq-cal-{uuid4().hex[:12]}"
        try:
            response = await client.generate(messages)
            row = {
                "recorded_at": recorded_at, "request_id": request_id, "attempt": index + 1,
                "status": "ok", "model": client.model, "model_ttft_ms": response.model_ttft_ms,
                "total_ms": response.total_ms, "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out, "headers": selected_headers(response.provider_headers),
            }
            append_result({"request_id": request_id, "status": "ok", "timing_ms": {
                "model_ttft": response.model_ttft_ms, "user_visible_ttft": response.model_ttft_ms,
                "total": response.total_ms}, "usage": {"tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out}, "retrieval_setting": "provider_calibration"},
                scenario="groq_baseline", source="groq")
        except ProviderError as error:
            row = {
                "recorded_at": recorded_at, "request_id": request_id, "attempt": index + 1,
                "status": f"http_{error.status_code}", "error": str(error),
                "headers": selected_headers(error.headers),
            }
            append_result({"request_id": request_id, "status": "rate_limited" if error.status_code == 429 else "error",
                "timing_ms": {}, "usage": {}, "retrieval_setting": "provider_calibration"},
                scenario="groq_baseline", source="groq")
        except Exception as error:
            row = {
                "recorded_at": recorded_at, "request_id": request_id, "attempt": index + 1,
                "status": "transport_error", "error": f"{type(error).__name__}: {error}",
                "headers": {},
            }
            append_result({"request_id": request_id, "status": "error", "timing_ms": {},
                "usage": {}, "retrieval_setting": "provider_calibration"},
                scenario="groq_baseline", source="groq")
        with MEASUREMENTS.open("a", encoding="utf-8") as output:
            output.write(json.dumps(row) + "\n")
        rows.append(row)
        if interval_s and index < calls - 1:
            await asyncio.sleep(interval_s)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=int, default=3)
    parser.add_argument("--interval-s", type=float, default=0)
    args = parser.parse_args()
    if not 1 <= args.calls <= 5:
        raise SystemExit("Use 1 to 5 controlled baseline calls.")
    for result in asyncio.run(measure(args.calls, args.interval_s)):
        print(json.dumps(result, indent=2))
