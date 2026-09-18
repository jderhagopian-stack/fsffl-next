# FSFFL NEXT - Gate A Frozen Routed-Fit Reproducibility Boundary

Checkpoint date: 2026-09-18

Authority: research-only continuation under the management-approved Y2/Y3 -> parity -> Shapley directive

Status: **STOP BEFORE GATE A MATERIALIZATION - REQUIRED FROZEN ROUTED FIT/OUTPUT NOT DURABLY AVAILABLE WITHOUT REFIT**

## 1. Recovered durable boundary

Authoritative research branch at recovery:
`research/future-state-resolution-phase34-resume`

Recovered branch head before this checkpoint:
`fc7823b38e9c8bc4ce8f89c4ac25e52e35425171`
(`research: freeze replacement identity materialization coordinate`)

Protected refs at recovery:
- `main`: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #147: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`

The replacement-coordinate manifest explicitly records:
- `downstream_y2_y3_materialized=false`;
- `sentinel_forecast_parity_run=false`;
- `intrinsic_or_shapley_run=false`;
- `ranking_output_inspected=false`.

Therefore Gate A, Gate B, and Gate C were all incomplete at recovery. No completed durable gate was rerun.

## 2. Durable inputs verified available

### Frozen Year-1 board
Coordinate:
`year1-current-governed-2026:2026-09-18T09:42:31.889752+00:00`

- rows: 335
- exact artifact SHA-256: `c668b74b9010809904c14366d992137f7b038b299d6d3f031b07eea0d63c0b3f`
- source Actions artifact: `10541375155`
- source ZIP SHA-256 reverified in this continuation: `c23fed641c4ad689513510022f187e6ea05cab2dc88d457d545be9afc1f49ee7`

No live provider refresh occurred.

### Approved replacement identity/materialization coordinate
Coordinate:
`replacement-identity-materialization-v1:2026-09-18T17:06:21Z`

- rows: 335
- row-material SHA-256: `1803ee0200b8d1d39dfd719934bd683765727bef997f2a1f1ee44d2a6444af56`
- stable population SHA-256: `095d09458bfe021e7b7075281e8430573514c6d1e5c2dae3d25430f555ceba4b`
- reload verification: PASS
- mappings: 73 DIRECT_ID, 227 EXACT_NAME_POSITION, 35 UNMATCHED
- prior-two coverage: 199 covered; missing-history and IDENTITY_UNMATCHED reasons preserved.

### Frozen historical PIT evidence
Phase 2 artifact:
- Actions artifact: `10486530017`
- ZIP SHA-256 reverified in this continuation: `f7e9cfeee05687d5eb44085124c112c70d812ba95f6d30ca1213c6f92d1ac6ff`
- player-season panel SHA-256: `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`
- corrected age/state rows SHA-256: `9c504c9e765bd113406b59185a3cc80d23cca2401ecf31857692e15720b29063`

### Frozen M1a + two-prior fit
The exact selected-candidate current-diagnostic M1a / consistency parameters remain durable and were not re-estimated:
- Y2 training rows 5,974; source seasons 2005-2022; M1a coefficient `0.07939942531895901`.
- Y3 training rows 4,781; source seasons 2005-2022; M1a coefficient `0.07812314495946265`.
- Exact prior-two transforms and 11 consistency coefficients for each horizon remain persisted in `IDENTITY_MATERIALIZATION_DEPENDENCY_RECOVERY_2026-09-18.json` and `CURRENT_PLAYER_SENTINEL_FINAL_DIAGNOSTIC_2026-09-18.json`.

## 3. Gate A blocker

Gate A requires row-complete Y2/Y3 routed probabilities/state details for all 335 players under:
- QB = A2+C+D;
- RB/WR/TE = A2+D;
followed by the already-frozen M1a and two-prior conditional-production adjustments.

The durable repository preserves historical out-of-sample routed **prediction checkpoints**, but no durable object found in the recovered state contains either:

1. the fitted current-cutoff routed estimator state required to score the 335 current rows (including the DictVectorizer feature state and LogisticRegression coefficients/intercepts for persistence and ordered positive-state threshold models for the routed A2+C+D / A2+D fits); or
2. a row-complete 335-player current routed Y2/Y3 output board that can be consumed without fitting.

The prior current-player sentinel result persisted only 39 detailed player records (8 named sentinels + 31 checkpoint rows), not all 335.

The surviving Phase 3/4 harness `scripts/run_phase34_challenger_validation_fast.py` constructs routed probabilities by calling `.fit(...)` on `LogisticRegression` models. Executing that path now against the historical data would therefore perform a refit/retraining operation. The authoritative downstream directive explicitly forbids refit, retraining, coefficient change, or a new training-window choice.

This continuation did **not** call any model `.fit(...)`, did not regenerate routed coefficients, and did not substitute the older PR #147 I1 path.

## 4. Exact missing reproducibility dependency

To proceed mechanically without violating the frozen-model rule, recover either:

- the exact fitted current-cutoff routed A2+C+D (QB) and A2+D (RB/WR/TE) estimator artifacts, including feature/vectorizer state and all fitted probability-model parameters needed to score current rows; **or**
- the exact row-complete 335-player routed Y2/Y3 output produced by those frozen fitted estimators before M1a/two-prior adjustment, with sufficient provenance to verify it is the selected frozen current diagnostic coordinate.

This is a reproducibility dependency, not permission to reconstruct or refit the model.

## 5. Gate status

- Gate A: **NOT EXECUTED - BLOCKED BEFORE MATERIALIZATION**
- Gate B: **NOT EXECUTED**
- Gate C: **NOT EXECUTED**
- No Y2/Y3 row was newly produced.
- No sentinel parity comparison was newly run.
- No Shapley/Intrinsic ranking was run or inspected.

## 6. Stop boundary

**STOP.**

Do not refit the routed probability model, choose a different training window, infer coefficients from sampled sentinel outputs, substitute the older PR #147 I1 Forecast path, tune to the eight sentinels, run partial-universe Shapley, implement, promote, merge, or deploy.

Management review is required at this exact reproducibility boundary.
