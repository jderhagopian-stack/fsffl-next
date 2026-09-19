# FSFFL NEXT - Future-State Resolution Phase 3/4 Bounded Challenger Protocol

Status: FROZEN BEFORE PHASE 3/4 CHALLENGER RESULTS ARE INSPECTED
Authority: research only under management Phase 3/4 bounded challenger directive
Production authority: unchanged; PR #147 must not be modified, merged, or deployed.

## Evidence and chronology

Use the authoritative Phase 2 point-in-time player-season panel and corrected age/state residual evidence. Preserve Phase 2 target semantics: a target production row is persistence; absence is non-persistence for this research coordinate, not a formal retirement declaration.

Primary evaluation source seasons follow the already-governed Integrated Forecast chronology:
- development: 2014-2018;
- validation: 2019-2020;
- untouched final holdout: 2021-2022.

For a test source season t and horizon h, a training transition is eligible only when its target season is strictly before t (source_season + h <= t-1). Predictor residuals remain those calculated point-in-time at their own source cutoffs. No named current player enters fitting, feature selection, threshold selection, or challenger selection.

The matched historical baseline is the frozen I1 reduced-path architecture re-estimated chronologically on the Phase 2 evidence: L2 logistic C=0.25, deterministic seed 20260915, persistence stage plus ordered useful+/starter+/premium+/elite stages, monotonic threshold clamping, and state-conditioned production means. H1/H2 are fit together; H3 is direct and separate, matching the frozen production architecture split. Reduced-path production/context/role features preserve frozen I1 transformations.

## Standalone A - exact-age survival/persistence

A modifies the persistence stage only. Ordered positive-state transitions and state means remain frozen-baseline form.

Two predeclared parsimonious age forms are compared on validation only:
- A1: replace coarse age-band one-hot with position-specific continuous exact-age terms;
- A2: A1 plus one late-career hinge for QB (>37) and RB/WR/TE (>31), plus a young-TE hinge (<24).

All exact-age terms are regularized by the same C=0.25 logistic model. The validation winner is frozen before final holdout. The final decision is driven by persistence Brier/log loss and subgroup calibration, not named-player behavior.

## Standalone B - within-state conditional-production carryover

B leaves all state probabilities unchanged. It adjusts production conditional on each positive realized future state through an empirically shrunk target-residual estimate.

Supported cells are frozen from Phase 2 evidence before Phase 3/4 results:
- QB: young/prime/aging, h1/h2/h3;
- RB: prime h1 only;
- WR: aging h1 and h3;
- TE: aging h1 and h2; prime h1.

Within each supported position/stage/horizon cell, Bayesian ridge regression estimates future within-state residual from current within-state residual using only training transitions. Weak cells collapse toward zero carryover. The predicted residual adjusts each positive state mean by the historical state SD; out remains zero. No coefficient is copied from Phase 2.

## Standalone C - multi-season residual memory

C tests prior-season age/state-adjusted residual history beyond frozen I1's latest/prior raw production features.

Probability-model memory features are permitted only for:
- prime/aging QB;
- aging WR;
- aging TE.
No RB production/state memory feature is added.

The prior age/state residual and coverage flag are regularized within the same persistence/ordered-logistic architecture. Separately, a conditional-production diagnostic compares current-residual-only versus current+prior-memory Bayesian ridge in the supported cohorts. A role-loss diagnostic compares frozen-feature logistic versus frozen-feature+memory logistic among source-established players. These diagnostics do not create a separate production authority.

## Standalone D - future-state transition calibration at production extremes

D leaves persistence and state means unchanged. It augments only conditional positive-state transition models with point-in-time within-current-state location:
- centered within-state percentile, position-specific;
- upper-tail hinge above the 80th percentile for current premium/elite states;
- lower-tail hinge below the 20th percentile for current premium/elite states.

Baseline tail calibration is reported first for lower (0-33%), middle (33-80%), and extreme-upper (80-100%) locations in current premium/elite states. If D does not improve transition/tail calibration, no tail correction is retained.

## Sensible combinations

After standalone definitions are frozen, evaluate:
- A+B;
- A+C;
- A+D;
- A+B+C+D.

All combinations are mechanical unions of the frozen standalone components. No new coefficients, thresholds, or features are introduced after standalone results are seen.

## Metrics

Report h1/h2/h3 separately and overall, plus position and career stage where support permits:
- persistence Brier/log loss and calibration gap;
- six-state multiclass Brier/log loss;
- conditional positive-state Brier/log loss;
- anticipated-production MAE/bias overall and conditional on persistence;
- tail calibration for premium/elite source states;
- role-loss Brier/log loss for the C diagnostic;
- era/split stability and sample support.

Materiality is interpreted in football terms. Tiny metric changes without replicated position/stage benefit do not justify added complexity.

## Sentinel gate

Only after historical challenger fitting/selection is complete, apply frozen baseline and selected challengers diagnostically to governed 2026 facts for Aaron Rodgers, Sam Darnold, Bijan Robinson, Jahmyr Gibbs, at least one elite WR, and elite TEs at different distances above the generic elite-TE mean. Named players cannot alter the historical selection.

## Stop

Produce the management report and STOP. No production implementation PR, PR #147 modification, merge, deploy, or authority change.
