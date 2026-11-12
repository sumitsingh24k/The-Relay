# Stand-in calibration and validation

## Calibration source

`calibrate_standin.py` read eight successful real Groq baseline measurements from `measurements/groq_baseline.jsonl` and generated `standin/calibration.json`.

- Base artificial delay: 639.141 ms (median-derived).
- Token delay: 1.0 ms (estimated from the observed post-first-token remainder and output-token median).
- Failure rate: 0.0 because no real transient baseline failure was observed; it is not inferred.
- Load slowdown factor: 0.25 per additional in-flight request.

## Server validation

A fresh stand-in process loaded `calibration.json`; its health endpoint returned the calibrated delay. Streaming `/v1/chat/completions` returned SSE `data:` chunks, a usage event, then `[DONE]`.

Local controlled checks also observed:

- RPM configuration of 1: second request returned HTTP 429 with `Retry-After: 1`.
- Failure rate configuration of 1: request returned HTTP 503.

These are stand-in observations, not claims about real Groq behavior.
