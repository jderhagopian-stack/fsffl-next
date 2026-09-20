# FSFFL NEXT — I1 final-fit + current-season adapter protocol

Status: FROZEN BEFORE FINAL-FIT / LIVE CURRENT-PLAYER OUTPUTS ARE OBSERVED
Authority: implementation only; does not promote production authority
Research authority: PR #146 frozen I1 architecture, provisional governed C=0.25
Production base: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`

## Purpose

Define the narrow production-artifact and live-adapter procedure needed to deploy the already-selected I1 architecture without reopening model selection, adding new coefficients, or allowing current-player output to tune Forecast.

## 1. Final model fit is not a new research search

The production artifact uses exactly the frozen I1 architecture and feature semantics:

- binary persistence logistic regression;
- conditional ordered `usable+`, `starter+`, `premium+`, `elite` logistics;
- deterministic monotonic threshold clamping;
- six final career-state probabilities;
- frozen hierarchical state-conditioned anticipated-production means;
- rich and reduced evidence paths;
- governed regularization policy with current default `C=0.25`;
- solver `lbfgs`, max iterations `2000`, seed `20260915`, minimum training rows `100`, minimum binary class count `15`.

There is no new C search, hyperparameter search, architecture comparison, named-player review, Value/Shapley feedback, market input, owner input, or downstream tuning.

## 2. Frozen calibration evidence era

The final fit may use only the same research evidence era declared by the frozen integrated Forecast protocol: source seasons 2012–2022, with chronologically available one- and two-year factual outcomes through 2024 where the frozen target contract resolves them.

Later source seasons must not silently enter coefficient estimation merely because newer data are now available. Extending the calibration era is a separate research/calibration decision.

For the deployment artifact:

- final production-state boundaries are fit per position from positive source-season production in the frozen source era only;
- the selected I1 model is then fit once from all eligible resolved frozen-era training examples using those governed final-fit coordinates;
- state-conditioned anticipated-production means are fit from the same final-fit examples;
- the resulting coefficients, intercepts, state means, state boundaries, coverage metadata and model/config versions are serialized into a deterministic JSON artifact;
- runtime inference loads the artifact; it does not refit I1 per request.

Any inability to reproduce the frozen research semantics is an implementation defect or blocker, not permission to alter the model.

## 3. Current-season source facts

Current-player prediction must use completed source-season football facts in the same semantic coordinate as training, not forward projection output masquerading as realized production.

For a 2026 evaluation the default completed source season is 2025. The current-fact artifact/adapter must preserve, when available:

- canonical player identity and position;
- completed source-season fantasy production in the same governed source coordinate used by the research panel;
- prior-season production in that coordinate;
- age / career stage and experience;
- games and position-appropriate opportunity (`QB=pass attempts`; `RB=carries+targets`; `WR/TE=targets`);
- opportunity per game;
- same-season / same-position role band (`weak` below the median; otherwise `established`);
- provenance and explicit coverage.

Forward full-season projections remain valid Year-1 Forecast evidence elsewhere in FSFFL, but they cannot substitute for these completed source-season I1 predictor facts.

## 4. Rich evidence remains optional and fail-closed

The current adapter must not invent organizational continuity, injury, reserve/practice, participation, or snap evidence.

If governed current source-season rich evidence is unavailable, I1 uses its frozen reduced-evidence path. Missing rich evidence is represented as missing/coverage false, never as healthy, active, retained, released, or non-persistent.

A future governed provider may supply the same canonical rich fact contract without changing I1 semantics, but it must pass canonical-adapter parity first.

## 5. Identity and current-player coverage

Current source facts must map to canonical live players deterministically. Preferred mapping is a stable provider/canonical player identifier. A fallback exact normalized-name + position mapping is allowed only when it is unique and observable; ambiguous identities fail closed.

A player without a completed source-season row is not automatically a zero-production player. Zero source production may be supplied only when factual provider evidence establishes that zero is the correct completed-source-season fact. Otherwise the player is unscored by I1 and the coverage report must say so.

Rookies/new entrants require an explicit factual treatment; no rookie bonus, youth bonus, pedigree override, or guessed zero is allowed.

## 6. Runtime insertion point

Do not create a parallel Intrinsic package or route.

Production wiring must flow through the existing authoritative surfaces:

`canonical football facts -> fsffl.forecast I1 -> fsffl.value frozen Shapley -> existing value runtime / product API -> downstream Team Utility / Decision / Search`

The obsolete surplus-over-replacement Intrinsic calculation must not be relabeled as Shapley. If the existing API result contract encodes replacement/surplus semantics, introduce a Shapley-native versioned result contract in `fsffl.value` and adapt the existing route explicitly rather than populating false fields.

## 7. Mandatory gates before management review

Before any promotion recommendation:

1. historical research parity must pass the predeclared tolerances;
2. serialized-artifact inference must match the in-memory final fit within numerical tolerance;
3. current canonical adapter coverage and fallbacks must be reported over the live 2026 universe;
4. live distribution/archetype sanity must be documented;
5. young/developmental cases must be audited without compensation/tuning;
6. the locked 10-point Intrinsic Constitution must pass;
7. determinism/runtime/failure behavior must be measured;
8. source/license/rights dependencies must be explicit.

No merge, deploy, production-authority promotion, or calibration change is authorized by this protocol.
