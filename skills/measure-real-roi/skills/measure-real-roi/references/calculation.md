# Calculation

## Terms

- `T`: time returned, in hours.
- `C`: new capacity, valued in dollars.
- `L`: line-item cost for the pilot period.
- `H`: human cost hours: learning, checking, fixing, and model-change redo.
- `O`: organizational cost: unused seats or infrastructure in dollars, plus coordination and cleanup hours.
- `R`: institution-wide standard hourly rate.

## Formula

```text
Real ROI = (T × R + C)
           ÷
           (L + H × R + O_dollars + O_hours × R)
```

A result of `1.0` is break even.

## Counting Rules

- For each aggregate weekly record, `time_saved = baseline_minutes - confirmed_harness_minutes`.
- For historical per-thread records, sum `baseline_minutes - confirmed_harness_minutes` across the sampled threads and report the sampled coverage separately.
- Negative time savings are allowed.
- If new capacity used saved time, count it under `C`, not `T`.
- Routine checking and fixing belongs in `H`.
- Downstream or organization-wide cleanup belongs in `O`.
- Coordination hours belong in `O`.
- Do not count the same hour in both `H` and `O`.
- Leave unknown values missing.
- Do not replace missing values with zero unless the participant explicitly said zero.
- If the denominator is zero, report the ratio as undefined.

## Evidence Labels

- `measured`: value comes from records.
- `reported`: participant confirmed or corrected the value.
- `derived`: value comes from timestamp analysis.
- `estimated`: participant recalled or inferred the value.
- `missing`: participant did not know or did not answer.

## Report

The report should include:

1. the ROI ratio
2. totals for `T`, `C`, `L`, `H`, and `O`
3. evidence quality by term
4. coverage and missingness
5. sensitivity results
6. non-monetized benefits
7. the renewal judgment and decision owner
8. what the unit would decide differently
