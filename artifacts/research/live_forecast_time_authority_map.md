# FSFFL NEXT — Live Forecast Time Authority Map

Status: **RESEARCH ONLY — recorded before direct h=3 results**

## Exact authorities inspected

### Completed-season I1

Source: frozen integrated Forecast research inherited from PR #146.

- A source record belongs to completed season `S`.
- Direct target truth is looked up at `S + h`.
- Frozen selected I1 was trained/evaluated for `h=1` and `h=2`.
- Therefore `h=1 = S+1` and `h=2 = S+2` by construction.
- I1 is persistence-first: a logistic persistence model is combined with ordered conditional state probabilities for useful+/starter+/premium+/elite; the resulting state distribution is mapped to anticipated production with factual state-conditional means.
- Rich and reduced evidence paths are selected from source-season evidence coverage. No future target facts enter source features.

### Current/live-season Forecast

Source: production `src/fsffl/forecast/current_runtime.py`, `in_season_runtime.py`, and `in_season_orchestration.py` on `main`.

- This is a distinct governed current-season Forecast authority, not completed-season I1.
- During an active season it combines production-to-date with remaining projection evidence under explicit as-of-week provenance.
- Its output is expected full-season/current-season production; realized points-to-date are an input, not the whole Forecast.
- This authority can legitimately own the evaluation calendar season if the live calendar bridge validates.

### Frozen Shapley consumer under PR #147

Source: `src/fsffl/value/shapley_intrinsic.py` on implementation PR #147.

- Frozen Monte Carlo count: 2,048 permutations.
- Frozen discount: 0.85.
- Frozen Shapley seed: 20260915.
- Consumer shape is a three-year vector: `current_points`, `year_2`, `year_3`.
- Year 1 is treated as a current-production deployment weight; future years are state-distributed Forecast inputs.
- Total is `Year1 + 0.85*Year2 + 0.85^2*Year3`.
- This consumer cannot determine Forecast calendar semantics; Forecast must freeze those first.

## Calendar mismatch that triggered this workstream

For a live request inside calendar 2026:

```text
completed factual source season S = 2025
live evaluation season E          = 2026

completed-source I1:
  h=1 -> target 2026
  h=2 -> target 2027
  h=3 -> target 2028  [NOT YET VALIDATED]

live/current-season Forecast:
  as-of date in 2026 -> target 2026
```

The existing two-horizon I1 therefore cannot honestly populate all three live calendar years 2026/2027/2028. Relabeling h=1 or h=2 would be false, recursively feeding forecasts back into I1 would change the model semantics, and treating partial 2026 facts as a completed 2026 source season would create an unresearched coordinate.

## Candidate calendar ownership if direct h=3 validates

```text
INTRINSIC DISPLAY     CALENDAR TARGET     FORECAST AUTHORITY
Year 1                2026                live/current-season Forecast
Year 2                2027                completed-2025 I1 h=2
Year 3                2028                completed-2025 direct I1 h=3

Diagnostic only:
completed-2025 I1 h=1 -> 2026 (same calendar target as live Year 1)
```

The diagnostic h=1 value must not be double-counted and must not be relabeled as 2027.

## Historical in-season PIT archive audit (Candidate B)

FSFFL has correct prospective storage infrastructure:

- `db/migrations/20260911_010_durable_projection_history.sql` creates append-only `fsffl.projection_snapshot` and `fsffl.projection_observation` tables with provider, season, horizon, week, effective/retrieved timestamps, versioning and immutable observations.
- The migration explicitly describes storage as evidence rather than Forecast calculation authority.
- `src/fsffl/forecast/projection_history.py` defines the application-level revision contract.

However, the live FSFFL NEXT Supabase project was queried before any h=3 result was inspected:

```text
fsffl.projection_snapshot row count: 0
minimum effective_at: null
maximum effective_at: null
seasons represented: 0
providers represented: 0
```

The durable table was introduced on 2026-09-11, so FSFFL currently has no internal historical weekly/provider snapshot archive from which to reconstruct 2014–2025 as-of-date projection information.

### Consequence

Candidate B (a genuine in-season PIT future-season model) is **excluded before testing**. The project can accumulate this evidence prospectively, but backfilling historical projection beliefs from later publications would be leakage and is prohibited.

## Research candidate remaining

The only predictive candidate advanced to evaluation is a direct completed-season `h=3` I1 extension, independently trained against factual S+3 outcomes at the frozen global `C=0.25`. Candidate C remains a calendar-ownership composition test after Forecast selection; it is not a predictive challenger.
