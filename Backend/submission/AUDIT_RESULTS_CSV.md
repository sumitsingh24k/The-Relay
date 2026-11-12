# Task 1: final results.csv audit

## Result

- Raw rows: **386**. Clean rows: **386**. The raw CSV was read only and not modified.
- Exact raw schema: **True**. Exact clean schema: **True**.
- Malformed rows: **0**. Invalid status values: **none**. Invalid non-empty clean grades: **none**.
- Raw duplicate request IDs: **18**. They are preserved in raw data; clean IDs are unique through documented suffix remaps.

## A/B/C evidence coverage

- Manual review IDs: **48**.
- IDs found in raw CSV: **48**. Missing review IDs: **0**.
- Reviewed rows by setting: A-small **16**; B-medium **16**; C-medium-expanded **16**.
- There are **6** additional retrieval rows. They are earlier ungraded stand-in trials, not silently deleted and not included in the 48-question comparison.

## Load evidence coverage

- `steady`: **17** raw rows
- `burst`: **25** raw rows
- `sustained_overload`: **127** raw rows
- `rpm_halved`: **26** raw rows
- `daily_budget_exhausted`: **34** raw rows

All five named load scenarios are represented. Repeated local attempts are preserved as evidence, so these counts are not presented as one clean run per scenario.

## Nulls and mappings

- `first_token_ms`: **315** blank raw values
- `total_ms`: **174** blank raw values
- `tokens_in`: **314** blank raw values
- `tokens_out`: **197** blank raw values
- `answer_grade`: **386** blank raw values

Blank token fields are expected for stand-in/retrieval-only rows because no real-provider usage is returned. Blank historical TTFT/total fields are retained rather than imputed. The clean copy maps genuinely reviewed internal labels to the allowed submission values only; raw grades remain blank.
