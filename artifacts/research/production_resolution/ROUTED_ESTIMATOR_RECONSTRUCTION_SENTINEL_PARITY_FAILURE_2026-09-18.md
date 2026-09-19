# FSFFL NEXT - Reconstructed Routed Estimator Sentinel Parity Check

Checkpoint date: 2026-09-18

Authority: reproducibility recovery only under the management-approved Y2/Y3 -> parity -> Shapley directive

Status: **FAIL - SENTINEL PARITY EXCEEDS 1e-6; STOP BEFORE GATE A BOARD**

## Authorized reconstruction

The lost ephemeral current-cutoff routed estimator was mechanically reconstructed from the surviving Phase 3/4 code and the same frozen historical artifacts.

No training-window, feature, routing, transform, model-family, hyperparameter, solver, random-state, or named-player rule was changed.

Recovered code constants and mechanics:
- routing: QB = A2+C+D; RB/WR/TE = A2+D;
- LogisticRegression C = 0.25;
- solver = lbfgs;
- max_iter = 2000;
- random_state = 20260915;
- DictVectorizer(sort=True);
- current fit cutoff: target outcomes observable through 2025, source rows through 2022;
- H1/H2 pooled fitting for the Y2 path; direct H3 fitting for Y3;
- monotone ordered positive-state thresholds unchanged;
- D state-percentile construction unchanged.

Frozen inputs used:
- Phase 2 archive artifact 10486530017;
- Phase 2 player-season panel SHA-256 c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7;
- Phase 2 corrected age/state rows SHA-256 9c504c9e765bd113406b59185a3cc80d23cca2401ecf31857692e15720b29063;
- activation artifact 10467264159 / current I1 facts SHA-256 dbea7f754e0910a83a85518880a5e3f649579116a205f9d30d8a4c9f39a7932d;
- approved replacement identity/PIT coordinate replacement-identity-materialization-v1:2026-09-18T17:06:21Z.

No coefficients were altered by hand and no parity-directed tuning was performed.

## Required pre-Gate-A parity

Directive requirement: reproduce the eight durable full-precision sentinel outputs before using the reconstructed estimator for the 335-player Gate A board. Acceptance tolerance: <= 1e-6 across routed probabilities and point fields.

The reconstruction immediately reproduced non-QB routed probability rows to displayed full precision. Example: Bijan Robinson Y3 reconstructed probabilities are exactly the durable routed values:

- out 0.0953045003335451
- depth 0.017445296044765555
- usable 0.03774640159660663
- starter 0.03635404580432719
- premium 0.19646169164039579
- elite 0.6166880645803597

However, the first decisive QB parity check fails.

### Aaron Rodgers Y2 routed probability discrepancy

Durable prior sentinel:
- out = 0.33457621892194744
- persistence = 0.6654237810780526

Mechanical reconstruction:
- out = 0.3345953571216298
- persistence = 0.6654046428783702

Absolute discrepancy:
- out/persistence = 0.00001913819968236 (approximately 1.91382e-5)

Required tolerance:
- <= 0.000001

The discrepancy is approximately 19.1 times the permitted tolerance.

Because routed probability parity already fails, the directive's stop condition is reached. The remaining sentinel/point comparisons are not used to tune, adjust, or reverse-engineer the reconstruction.

## Interpretation of boundary

The surviving historical fit procedure is sufficiently recovered to reproduce non-QB sentinel probabilities exactly, but the reconstructed QB A2+C+D path does not reproduce the durable Aaron Rodgers full-precision output within the authorized tolerance when supplied with the approved replacement PIT coordinate.

This means exact parity of the lost ephemeral sentinel estimator has **not** been proven. Possible causes are not adjudicated here; doing so by adjusting inputs, coefficients, solver behavior, or fitting details to force the durable value would violate the no-tuning rule.

## Gate status

- estimator reconstruction attempt: EXECUTED AS AUTHORIZED
- eight-sentinel parity gate: **FAIL**
- Gate A 335-player board: **NOT EXECUTED**
- Gate B: **NOT EXECUTED**
- Gate C / Intrinsic / Shapley: **NOT EXECUTED**
- no rankings inspected
- no production/model authority changed

## Stop boundary

**STOP.**

Do not tune the reconstruction to Aaron Rodgers or any other sentinel. Do not alter the approved replacement PIT coordinate, training population/window, features, routing, transforms, model family, hyperparameters, solver settings, random state, or coefficients. Do not proceed to the 335-player Gate A board, Gate B, or Gate C without a new management decision or newly recovered provenance-identical dependency that resolves the parity discrepancy.
