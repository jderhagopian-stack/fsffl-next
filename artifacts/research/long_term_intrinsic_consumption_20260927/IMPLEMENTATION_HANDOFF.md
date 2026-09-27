# Bounded Implementation Handoff — Long-Term Intrinsic

Date: 2026-09-27  
Status: **RESEARCH HANDOFF / NO PRODUCTION PROMOTION**

## Proposed contract identity

- Value model: `long-term-intrinsic-shapley-y4-y7-v1`;
- raw quantity: `mean_annual_governed_shapley_marginal_fantasy_points_y4_y7`;
- presentation scale: `fsffl-long-term-intrinsic-index:long-term-y4-y7-v1`;
- horizons consumed: Y4, Y5, Y6, Y7;
- Y8 cardinal consumption: **forbidden**;
- permutations: 2,048;
- base Shapley economics: existing governed lineup-capacity game.

## Consumer module

Implement a new Value-owned pure consumer, separate from Current Intrinsic.

Suggested boundary:
`src/fsffl/value/long_term_intrinsic.py`

Inputs:
1. canonical league rules;
2. governed Y4-Y7 Forecast contract;
3. per-horizon exact-or-supported policy set;
4. per-policy annual central Forecast;
5. per-policy annual within-model uncertainty;
6. Forecast/model/provenance versions.

Forbidden inputs:
- Market;
- owner identity/preferences;
- team competitive state;
- trade/package context;
- current player market value;
- manual youth/age/workload adjustments.

## Per-horizon calculation

For h = Y4..Y7:
1. materialize the exact policy if the Forecast authority cell is exact;
2. otherwise materialize every supported policy in the frozen authority set;
3. for each supported annual Forecast, compute expected Shapley marginal lineup contribution using the existing league-aware Shapley game;
4. propagate governed annual 80/90 uncertainty through the same scenario mechanism;
5. persist every policy-specific annual contribution and its provenance.

Do not select a hidden winner in set-valued cells.

## Four-year calculation

For every admissible policy path:

`LT_RAW(path) = mean(phi4, phi5, phi6, phi7)`.

The efficient rectangular envelope is:
- mean of per-year supported minima;
- mean of per-year supported maxima.

Return:
- `raw_authority_low`;
- `raw_reference_center = midpoint(low, high)`;
- `raw_authority_high`;
- four annual contribution records.

The midpoint is presentation-only.

## Uncertainty fields

Keep two objects.

### Model authority
```
model_authority:
  kind: set_valued_forecast_policy
  low
  high
  width
  exact_horizons
  unresolved_horizons
  policy_sets_by_horizon
```

### Within-model
```
forecast_uncertainty:
  annual:
    y4: {lo80, hi80, lo90, hi90, evidence}
    ...
  aggregate:
    interval_arithmetic_80
    interval_arithmetic_90
    covariance_validated: false
```

A combined outer band may be supplied for presentation, but may not replace the two source objects.

Do not emit a long-term standard deviation until cross-horizon covariance is validated.

## 0-10,000 presentation

Use a separate percentile/rank-calibrated index:
- rank the governed eligible current cohort by `raw_reference_center`;
- convert percentile to the shared 0-10,000 presentation ruler;
- retain percentile;
- retain raw envelope.

The API must include a warning/semantic field that Current and Long-Term indexes are not additive.

## Persistence identity

The Long-Term Intrinsic fingerprint must include:
- league rules / lineup structure;
- evaluation/source season;
- Y4-Y7 Forecast contract version;
- exact symmetric authority-map version/hash;
- policy/model versions used per horizon;
- uncertainty artifact versions;
- Value model version;
- Shapley permutations;
- Shapley seed/horizon seed derivation;
- display-scale version.

Do not include volatile presentation timestamps in semantic identity.

## Proposed endpoint / artifact

Shadow first:
- artifact kind: `long_term_intrinsic_contract`;
- endpoint after implementation gate: `/api/value/long-term-intrinsic-v1`.

No existing Current Intrinsic endpoint is replaced.

## Required deterministic tests

1. Y4-Y7 all present; Y8 ignored/rejected for cardinal contribution.
2. Exact QB-Y5 and WR-Y5 policies are enforced.
3. Every other Y4-Y7 cell preserves its supported policy set.
4. No hidden policy selection.
5. Shapley efficiency residual within numerical tolerance.
6. Monotonic annual scenario behavior.
7. Four-year raw equals arithmetic mean of annual contributions.
8. Model-authority low <= center <= high.
9. Within-model and model-authority uncertainty serialized separately.
10. No cross-horizon SD when covariance is unavailable.
11. No Market/owner/team/trade inputs accepted.
12. Current Intrinsic output is byte/semantic unchanged.
13. Display index is rank-calibrated and separately versioned.
14. Rebuild/reuse fingerprint is stable for semantically identical inputs.
15. League-agnostic rule derivation tested on more than the current FSFFL lineup before promotion.

## Promotion sequence

This handoff authorizes only a bounded implementation/shadow phase after Management approval.

Promotion still requires:
1. runtime Y4-Y7 Forecast materialization for the supported policy sets;
2. deterministic replay against this Research evidence;
3. current 335-player full authority-envelope materialization;
4. resource/performance acceptance on the beta runtime;
5. API/presentation validation;
6. physical mobile validation;
7. explicit Management promotion.

Do not alter production Current Intrinsic while building the shadow.
