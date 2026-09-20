# FSFFL NEXT — Forecast + Intrinsic production implementation validation protocol

Status: FROZEN BEFORE IMPLEMENTATION PARITY / LIVE VALIDATION RESULTS
Authority: management production implementation directive dated 2026-09-15
Production base at freeze: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
Research evidence: PR #146, frozen I1 C=0.25, frozen Shapley W / discount 0.85 / B4 / 10-point Constitution

## 1. Boundaries

This branch implements and validates the already-selected I1 Forecast and frozen Shapley candidate. It does not reopen Forecast model-family research, the Intrinsic Constitution, B4 holding governance, W, discounting, Primitive A/D2, market/owner/trade inputs, or production authority. It must not merge or deploy itself.

Forecast parameters are not selected or tuned using Value/Shapley output. Named players are diagnostics only. No youth bonus, named-player override, blanket uplift, haircut, market price, ADP, fantasy ownership, owner behavior or trade behavior may enter Forecast or Intrinsic.

## 2. Frozen candidate

I1 is fixed at `C=0.25`, random seed `20260915`, `lbfgs`, max iterations 2000, minimum training n=100 and minimum binary class count=15. It consists of:

1. regularized binary persistence logistic;
2. conditional-on-persistence ordered binary thresholds for useful+, starter+, premium+, elite;
3. monotonic threshold clamping;
4. final six-state probabilities `out`, `depth`, `usable`, `starter`, `premium`, `elite`;
5. state-conditioned anticipated production from the frozen hierarchical state-mean estimator.

Rich-evidence and reduced-evidence paths remain distinct. Missing canonical evidence never implies healthy, retained, released, active, dead or non-persistent; it triggers explicit coverage/fallback behavior.

## 3. Canonical provider-neutral football facts

The production boundary exposes canonical facts only: position, age/career stage, experience, current/prior production and trajectory, role/opportunity, organizational attachment, roster continuity, release/team churn, active returns, practice/reserve history, injury/availability, participation trajectory, and evidence coverage. Provider-specific raw status codes are confined to adapters.

Non-IR injury and temporary organizational absence remain distinct from disappearance/non-persistence. Provenance and coverage/fallback path must be observable.

## 4. Predeclared numerical parity tolerances

These tolerances are frozen before implementation mismatches are examined:

- canonical feature-vector fixture equivalence: exact keys and max absolute numeric difference `<= 1e-12`;
- per-state Forecast probability parity: max absolute difference `<= 1e-8`;
- persistence probability parity: max absolute difference `<= 1e-8`;
- anticipated-production parity: max absolute difference `<= 1e-6` fantasy points;
- aggregate historical Forecast metrics (Brier/log loss/MAE/bias): absolute difference `<= 1e-6` from the frozen research harness when computed over the same rows;
- 2,048-permutation Shapley aggregate MAE difference: `<= 0.25` points;
- 2,048-permutation Shapley aggregate Spearman versus frozen research output: `>= 0.999` when compared player-by-player on the same fixture;
- per-player Shapley absolute difference: `<= 0.50` points on the parity fixture;
- Shapley efficiency residual: relative absolute residual `<= 1e-8`;
- locked Intrinsic Constitution: `10/10` principles pass exactly.

A tolerance failure is an implementation/data defect to diagnose, not permission to retune I1 or Shapley.

## 5. Validation gates

### Gate 1 — Research parity
Reproduce the frozen I1 outputs and downstream 2,048-permutation Shapley fixture using production modules. Compare to the frozen PR #146 artifact under the tolerances above. Expected research targets are State Brier ~0.117, State log loss ~1.422, anticipated-production MAE ~36.20, bias ~+1.06, downstream Shapley MAE vs realized H3 ~42.84, and downstream Spearman ~0.884; these are verification targets, never tuning objectives.

### Gate 2 — Canonical data parity
Equivalent canonical football facts constructed from different provider/raw-code fixtures must produce identical model inputs and outputs. Every mapping, fallback and coverage flag must be documented.

### Gate 3 — Current-season coverage
Run the governed current-season adapter over the live 2026 player universe. Report rich-evidence, reduced-evidence, fallback/unscored rates by position and relevant archetype. Missing evidence must fail closed.

### Gate 4 — Live sanity diagnostics
Inspect the full output distribution and diagnostics for elite established players, ordinary starters, aging veterans, rookies, young backups, injured players, temporary absences, practice/reserve players, low-production attached players, and true fringe/no-use rights. Named examples are illustrations only.

### Gate 5 — Developmental-risk audit
Inspect probability distributions and football-state reasons for young/developmental rights. The known research limitation (7 of 21 true-developmental cases above 0.50 useful probability) remains visible. Fix only demonstrated implementation/data defects; never add a youth premium.

### Gate 6 — Structural / constitutional regression
Re-run the locked 10-point Intrinsic Constitution and confirm B4 separation, market independence, roster neutrality, scarcity behavior, zero/no-use behavior, useful-production positivity and elite separation.

### Gate 7 — Performance / operability
Measure deterministic repeatability, runtime, 2,048-permutation Shapley stability/efficiency, failure behavior, and safe reuse/caching opportunities. No semantic changes are allowed solely for latency.

### Gate 8 — Commercial-source readiness
List each live football-state fact family, current supplier, license/rights status, and replaceability. Research-only or legally uncertain sources must be explicitly identified. Source abstraction is required; commercial readiness must not be claimed while rights remain unresolved.

## 6. Stop conditions

- **SUCCESS**: research parity, acceptable live canonical coverage, coherent sanity diagnostics, no concrete developmental implementation/data defect, Constitution pass, and explicit source dependencies.
- **BLOCKED**: current canonical evidence cannot be sourced/mapped safely enough to reproduce the frozen semantics.
- **DEFECT FOUND**: fix only the demonstrated implementation/data defect and rerun affected gates.
- **MODEL CONCERN**: document precisely and return to management; do not redesign I1 in this branch.

## 7. Handoff decision vocabulary

The final implementation recommendation must be exactly one of:

- `READY FOR MANAGEMENT PROMOTION REVIEW`
- `NOT READY`
- `BLOCKED`

No merge, deploy or authority promotion is authorized by a successful implementation validation.