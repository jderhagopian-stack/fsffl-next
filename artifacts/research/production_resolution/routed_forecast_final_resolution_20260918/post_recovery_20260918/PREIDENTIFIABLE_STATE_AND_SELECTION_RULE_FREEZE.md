# Routed Forecast — pre-identifiable career-state and route-selection freeze

Date: 2026-09-18  
Study: Routed Forecast Final Resolution — post-Stage-0 continuation  
Status: **FROZEN BEFORE CANDIDATE-BY-STATE PERFORMANCE INSPECTION**

## Live starting state

- research branch recovered head: `9f110204229ac2bcef0644cd7591f4e697aaba0c`
- main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #147: open/unmerged; head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`
- compact coordinate: `routed_forecast_aligned_candidate_coordinate_compact_v1.csv`
- compact coordinate SHA-256: `8095788e1b48028c50b65d7fba51ac48a41daceeaa6459ae3a219723ce30b1eb`
- integrity check: exact hash match; 4,287 rows / 18 columns.

Stage 0 is not rerun.

## Source-time career/development state

Use NFL experience at the forecast cutoff only.

- `developmental_0_3`: experience <= 3
- `established_4_8`: experience 4 through 8
- `veteran_9_plus`: experience >= 9

Why this state:
- It is known at the forecast cutoff.
- It is football-coherent without using future outcomes.
- It uses three broad bands rather than outcome-tailored age cutoffs.
- Position remains a separate routing dimension, so the same experience band need not imply the same aging behavior at QB, RB, WR and TE.
- The labels do not assume that every young player is ascending or every veteran is declining.

No age threshold, future collapse outcome, current-player identity, source-percentile threshold, holdout result or candidate error was used to define the bands.

## Support guardrail

A position x career-state route is eligible for candidate assignment only when each fold used as evidence for that candidate/horizon has at least 20 observations.

Cells below this floor are sparse and default to B2a. This is an anti-fragmentation guardrail, not a fitted coefficient.

H2 has no leakage-free early fold by construction. H2 may therefore be evaluated only where its documented mid and validation rows exist, and both of those folds must satisfy the same support floor.

## Candidate universe and complexity order

Baseline: universal B2a.

Permitted already-developed alternatives:
1. R1
2. R2
3. H2 where legally observed

Complexity preference when evidence is effectively tied:
B2a / position-only routing > position x career-state routing; R1 > R2 > H2 when the richer treatment does not show a replicated incremental benefit.

No new candidate, coefficient, data family, H4, production haircut, structural-risk surface or current-player rule is authorized.

## Pre-holdout route evidence rule

For a candidate to replace B2a in a route:

1. It must have lower paired absolute error than B2a in every sufficiently supported chronological fold available for that candidate at that horizon.
   - R1/R2: early, mid and validation.
   - H2: mid and validation only, because early H2 is structurally unavailable.
2. The direction of mean signed error must not reveal a new large systematic overprediction/underprediction failure relative to B2a.
3. Role-loss and deep-collapse performance are reported as stress tests, not automatic vetoes. A route is rejected only if the stress evidence reveals a broad systematic failure that materially undermines the claimed overall gain.
4. Upper-tail and developmental-player calibration must be reported; they do not create a new route unless the broad MAE replication rule also passes.
5. If more than one candidate passes for the same cell, prefer the less complex treatment unless the richer candidate's incremental benefit is itself chronologically replicated.
6. Y2 and Y3 may differ only when their own fold evidence supports the difference.
7. Weak, mixed, unsupported or sparse evidence defaults to B2a.

Paired resampling/uncertainty summaries may be used to describe whether an apparent gain is distinguishable from noise. They are evidence summaries only and do not fit or alter Forecast predictions.

## Simplicity challenger

Position-only routing is evaluated under the same chronological replication rule. If position-only routing is effectively indistinguishable from a position x career-state challenger within paired uncertainty, position-only wins on complexity.

## Holdout/current board

Neither is used for discovery or selection. Any permitted holdout evaluation occurs only after the complete routing specification is frozen. The current-player board may be used only after a legitimate candidate freeze and only as a one-time sanity diagnostic.

## Execution accounting at freeze

- Forecast reruns: 0
- Forecast refits: 0
- recovered coordinate regenerated: no
- holdout used: no
- current-player board used: no
- candidate-by-state performance inspected before this freeze: no

Proceed to candidate-by-position/state scorecard using this frozen definition and rule.
