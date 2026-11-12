# CSV audit

## Schema

Expected columns and raw columns match exactly: `True`.
Raw rows: 379. Malformed rows: 0.

## Integrity findings

Duplicate non-empty request IDs: 18. The raw file is preserved unchanged.
The clean copy has unique IDs; 18 later duplicate occurrences received a `-duplicate-N` suffix. See `csv_id_remaps.json`.

## Missing values

- `first_token_ms`: 309
- `total_ms`: 172
- `tokens_in`: 307
- `tokens_out`: 194
- `answer_grade`: 379

Missing token values are expected for the local stand-in and retrieval-only fallbacks because neither reports Groq token usage. Missing TTFT occurs for buffered refusals/errors and older rows created before the distinction was logged.

## Scenario coverage

- `burst`: 25 raw rows
- `daily_budget_exhausted`: 34 raw rows
- `groq_baseline`: 8 raw rows
- `interactive`: 88 raw rows
- `retrieval_A-small`: 18 raw rows
- `retrieval_B-medium`: 18 raw rows
- `retrieval_C-medium-expanded`: 18 raw rows
- `rpm_halved`: 26 raw rows
- `steady`: 17 raw rows
- `sustained_overload`: 127 raw rows

The five required load scenario names and all A/B/C retrieval scenario names are present. Failed/rate-limited rows are retained rather than silently dropped.

## Grade mapping

The raw CSV is retained. The clean submission CSV maps reviewed internal grades to the brief's required values: `correct_cited` → `correct`; `correct_refused` → `refused_correctly`; `wrong`/`unsupported`/`incomplete` → `wrong`. Unreviewed answers remain blank.
