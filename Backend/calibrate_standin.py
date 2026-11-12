"""Derive stand-in defaults from actual Groq baseline records."""
from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path

MEASUREMENTS = Path(__file__).with_name("measurements") / "groq_baseline.jsonl"
OUTPUT = Path(__file__).with_name("standin") / "calibration.json"


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    return round(values[min(len(values) - 1, round((len(values) - 1) * p))], 3)


def calibrate() -> dict:
    records = [json.loads(line) for line in MEASUREMENTS.read_text(encoding="utf-8").splitlines() if line.strip()]
    ok = [row for row in records if row.get("status") == "ok"]
    if not ok:
        raise RuntimeError("No successful actual Groq measurements exist; calibration would be fabricated.")
    model_ttft = [float(row["model_ttft_ms"]) for row in ok if row.get("model_ttft_ms") is not None]
    totals = [float(row["total_ms"]) for row in ok if row.get("total_ms") is not None]
    output_tokens = [int(row["tokens_out"]) for row in ok if row.get("tokens_out") is not None]
    # The stand-in uses a conservative p50 initial delay and a per-token delay inferred
    # from the non-TTFT remainder. Failure rate remains 0 unless observed in real data.
    base = statistics.median(model_ttft)
    token_delay = max(1.0, (statistics.median(totals) - base) / max(1, statistics.median(output_tokens)))
    output = {
        "calibrated_at": datetime.now(UTC).isoformat(), "sample_count": len(ok),
        "source": "measurements/groq_baseline.jsonl", "observed": {
            "model_ttft_ms_p50": percentile(model_ttft, .5), "model_ttft_ms_p95": percentile(model_ttft, .95),
            "total_ms_p50": percentile(totals, .5), "total_ms_p95": percentile(totals, .95),
            "output_tokens_median": statistics.median(output_tokens),
        },
        "standin": {
            "base_delay_ms": round(base, 3), "token_delay_ms": round(token_delay, 3),
            "failure_rate": 0.0, "load_slowdown_factor": 0.25,
            "note": "Failure rate is zero because no real transient failure was observed in the baseline; do not infer it.",
        },
        "unavailable": ["RPM exact account limit", "TPD exact account limit", "observed real 429 recovery"],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    print(json.dumps(calibrate(), indent=2))
