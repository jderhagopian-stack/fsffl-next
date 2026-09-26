# FSFFL NEXT — FUMBLES_LOST Current-Input Assessment

Updated: 2026-09-26 UTC

## Question

Can existing canonical Forecast opportunity coordinates improve the first-party `FUMBLES_LOST` model without circularity, future leakage, or horizon incoherence?

## Retained canonical Forecast evidence inspected

Supabase FSFFL project:
- project: `gldxkbqcprzuffgmamxl`;
- retained preseason/raw ensemble artifact: `fsffl.derived_artifact id=145`;
- source artifact lineage: current Forecast artifact 94;
- raw observations: **1,675**;
- players: **335**;
- artifact as-of: `2026-09-10T21:36:41.346326Z`;
- provider effective time: `2026-09-10T13:32:43Z`.

Retained metrics:
- pass yards / pass TD / interceptions: 61 players each;
- rush yards / rush TD: 335 players each;
- receptions / receiving yards / receiving TD: 274 players each;
- no `FUMBLES_LOST`;
- no passing attempts;
- no sacks/dropbacks;
- no carries;
- no targets.

## Finding

The current retained Forecast bundle is useful point-in-time evidence, but it does **not** contain the same opportunity variables used by the accepted model.

Using projected yards or TDs as a proxy for attempts/carries/targets would create a new modeling assumption not established by this directive.

More importantly, FSFFL does not currently retain equivalent Week-2 point-in-time provider Forecast snapshots for 2023–2025 that would permit the exact feature to be tested chronologically out of time.

Therefore v1 does **not** promote the retained season Forecast coordinates as model features.

This is a governed negative finding, not a data omission.

## Accepted current point-in-time inputs

The accepted v1 uses Data-layer current football outcomes through canonical `completed_through_week=2`:
- QB attempts;
- QB sacks suffered;
- carries;
- receptions.

The production FSFFL Data layer already supports arbitrary provider weekly stat keys through `SleeperWeeklyStatsSource`; implementation must map the exact required stat semantics and fail closed if a needed current input is unavailable.

Research used the governed nflverse weekly outcome family to reconstruct historical OOT folds and the current shadow. Production may use an already-authorized first-party/current Data adapter only if it produces semantically equivalent current inputs and preserves capture/effective provenance.

## Current State coherence

Current FSFFL canonical State:
- state hash: `4052c99b01b586a328dea780e83de3f5e4bbc6d58134285746f9b5c0b3826294`;
- as-of: `2026-09-26T02:07:22.445124Z`;
- `completed_through_week=2`.

That exactly matches the accepted OOT input cutoff.

No later-week data are required or silently ignored relative to canonical State.

## Future expansion

A later model may test provider Forecast opportunity inputs if FSFFL first accumulates genuine PIT history for those fields across multiple seasons/cutoffs.

Until then:
- do not use current-only provider projections as an unvalidated historical feature;
- do not reverse-engineer carries/targets/attempts from projected yards;
- do not use fantasy points as a circular predictor of a component used to build fantasy points;
- do not alter other Forecast coordinates to make this model work.
