# FSFFL NEXT - Forecast-wide walk-forward revalidation diagnostic specification

Research-only validation stage. Frozen starting coordinate: research head 130550dd926f74a08e90f6d7c07b969c0f325d6c. PR #147, main, production runtime, P0/D1 authority, Value, Intrinsic, Shapley, Simulation, league scoring, merge, and deploy are out of scope.

## Canonical origins

- Y2: source seasons 2014-2023 inclusive.
- Y3: source seasons 2014-2022 inclusive.
- Minimum-history start remains 2014.
- At each origin T, the exact frozen D0/D1 methodology is replayed using only rows whose outcomes are resolved by T-1.
- Historical predictions 2014-2022 must reproduce the durable artifact. Source-2023 Y2 is generated only by exact replay of the same frozen methodology.

## Frozen decisions under review

The audit records both original P0 routing and later research-earned decisions. No route is automatically changed here.

- Y2 P0: D1 for every position x career-stage route.
- Y3 P0:
  QB developmental D0; QB established/veteran D1.
  RB developmental D1; RB established/veteran D0.
  WR developmental/established D1; WR veteran D0.
  TE developmental/established D1; TE veteran D0.
- Previously earned under the Forecast-wide proper-score research standard:
  QB Y3 developmental D0 -> D1.
  RB Y3 established D0 -> D1.
- Unresolved structural representation:
  RB Y3 developmental remains D1 as frozen control, with the high-source production-magnitude issue unresolved.

## Scoring and temporal robustness

For every position x horizon x career-stage cell compare the frozen research-current representation with the opposite frozen D0/D1 alternative.

Primary proper score: raw-point CRPS.
Point guardrail: raw-point absolute error / MAE.
State calibration: active Brier/log loss and six-state Brier/log loss from the shared state layer; candidate-independent but reported as context.
Conditional-active bias: predicted conditional-active points minus realized active target points, both raw and retention-normalized.

Report:
- pooled mean gain current minus alternative;
- player x source-year Bayesian bootstrap 95% interval;
- per-origin gain;
- origins improved / eligible origins;
- median origin gain;
- worst-origin regression;
- leave-one-origin-out pooled gain range and whether any omitted origin flips the pooled sign;
- moving source-year block-bootstrap sensitivity with block length 2 for Y2 and 3 for Y3.

No post-hoc composite score.

## Continuous production-magnitude diagnostic

Magnitude is treated as continuous evidence, not as a model state. For each adequately supported route:
- source_percentile is the primary normalized magnitude coordinate; raw source_points is retained for interpretation.
- Report binned descriptive smooths only for visualization, using fixed deciles where support permits.
- Fit diagnostic regressions only to realized outcomes / frozen forecast errors; these are not Forecast candidates.
- Compare three prespecified structural forms using the same rows:
  1. linear in centered source_percentile;
  2. quadratic smooth: linear + squared centered source_percentile;
  3. one-knot continuous piecewise linear form on the fixed diagnostic grid {0.60, 0.70, 0.80, 0.90}.
- Compare BIC and origin-level recurrence. A hard transition is not recognized unless the same knot is preferred in at least 60% of adequately supported origins and pooled change-point uncertainty is concentrated at that knot; otherwise classify as smooth/nonlinear or insufficient.
- A quadratic form is treated as evidence of smooth nonlinear curvature only if it beats linear pooled BIC by at least 6 and its curvature sign is stable in at least 60% of adequately supported origins.
- If neither nonlinear criterion is met, retain smooth monotonic/approximately linear unless evidence is insufficient.
- Diagnostic percentile slices p75+, p90+, p95+ are reported only for influence and human interpretation; they do not define states or authority.

Primary realized outcomes:
- expected retention = target_points / source_points including out as zero;
- active retention = target_points / source_points among target-active rows;
- inactivity / persistence;
- D0/D1 forecast CRPS difference and conditional-active bias versus magnitude.

Adequate origin support for a route-level structural fit is >=20 rows in that origin. Pooled structural reporting requires >=4 adequately supported origins.

## Revalidation dispositions

Each frozen decision is classified:
- CONFIRMED: broader walk-forward evidence supports the current research decision without material temporal fragility.
- WEAKENED: pooled evidence still points the same direction but uncertainty / temporal stability is materially weaker.
- REVERSED: the opposite frozen D0/D1 representation is materially supported under the canonical framework.
- UNRESOLVED: no frozen alternative safely resolves a structural concern or evidence is mixed/insufficient.

This stage validates; it does not promote, implement, or silently replace authority.
