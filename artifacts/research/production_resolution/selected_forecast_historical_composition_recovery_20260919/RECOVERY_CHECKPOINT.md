# FSFFL NEXT - Selected Forecast Historical Execution + Composition Recovery Audit

Date: 2026-09-19

## Final classification

**PARTIAL RECOVERY - MANAGEMENT DECISION REQUIRED**

## What the forensic record proves

The September 18 selected candidate that actually generated the surviving 335-player / 670-row board was:

**fixed routed Forecast -> frozen M1a -> exact frozen two-prior-season consistency**

with routing **QB=A2+C+D; RB/WR/TE=A2+D**.

The historical final diagnostic records Gate A execution over all 335 players, 670 Y2/Y3 rows, canonical SHA-256 `723f14076f5d0b8801cfff731c8a533494a9d8bbf98531bf25e2d45a16ce1fe8`, and no refit/reselection/routing/coefficient/feature change. Gate B records exact eight-sentinel parity with maximum numeric difference **0.0** at tolerance <=1e-6.

The exact board later survived provenance closure as Library `replacement_board.json`; `CHECKSUMS.txt` states it was copied byte-for-byte from the surviving runtime artifact and independently records the same governed canonical hash.

## Recovered September 18 composition

M1a is a no-intercept Bayesian ridge of target within-state residual-z on current within-state residual-z. It changes only positive-state means:

`m1a_z = beta_h * current_resid_z`

`mean_after_m1a(s) = max(0, baseline_mean(s) + m1a_z * frozen_training_state_sd(s))`

Final-current coefficients:
- Y2: 0.07939942531895901
- Y3: 0.07812314495946265

The two-prior layer is explicitly fitted to the **residual remaining after M1a**. Features are prior-two residual-z mean, absolute gap, and coverage; covered mean/gap are standardized with training-only population moments; uncovered continuous values are zero with coverage=0. The full transform moments and 11-term coefficient vector for each horizon are preserved in the companion JSON manifest.

It then adjusts the same positive-state conditional-mean coordinate:

`final_mean(s) = max(0, mean_after_m1a(s) + consistency_z * frozen_training_state_sd(s))`

Probabilities remain frozen. Out-state mean is zero. Final expected points are the probability-weighted sum of final state means.

## The D0/D1 question is resolved chronologically

The D0/D1 deployment specification was first frozen at commit `53794cbdce0c5d2762f5f461c93c42c45a858606` on **2026-09-19 04:44:43Z**.

The surviving selected-candidate board was already executed and checkpointed on **2026-09-18**, with final diagnostic commit `4ea39b9b03e25fbc92550b0d709f8e0cc440445a` at **19:22:26Z**.

Therefore the September 18 board was **not** produced by D0/D1. D0/D1 is a later redevelopment, not a missing upstream layer of that historical execution.

The later D1 model also embeds prior2 mean/gap/coverage directly inside its fitted production BayesianRidge and does not include the separately frozen M1a layer. Its research outcome was **B - not ready for promotion**.

## Why this is PARTIAL RECOVERY

The old historical execution is strongly recovered. The unresolved questions are cross-generation model-authority decisions that history cannot answer:

1. keep the September 18 routed+M1a+separate-prior2 producer, or replace it with September 19 D0/D1;
2. if D0/D1 is used, whether/how M1a should be retained and what residual/state-SD coordinate it should use;
3. if D1 is used, whether the old separate prior2 layer must be removed/redefined because D1 already consumes prior2 internally.

Choosing among those would create a new composition rule. This audit does not make that choice.

## Replay / board status

No new D0/D1->M1a replay was run because no historical specification for that cross-generation stack exists and reverse-engineering from the surviving board is prohibited.

The surviving 670-row board itself was recovered byte-for-byte and its canonical hash matches the historical execution record. The historical execution already passed exact sentinel parity at max difference 0.0.

## Protected boundaries

No PR #147 runtime change, no main change, no refit/retraining/retuning/reselection, no coefficient estimation, no new composition, no merge, and no deploy.

STOP for management decision.
