# Multi-Year Intrinsic Value — Empirical Guardrails

Status: research-only companion to PR #131. Nothing in this document changes production Forecast, Value, Team Utility, Decision, Search, or Simulation authority.

## Replacement definition is a model-selection problem

Do not assume a single replacement baseline. Compare at least these league-level candidates on strict chronological holdouts:

- starter threshold;
- marginal lineup opportunity;
- first rostered replacement / replacement-pool boundary;
- replacement-pool quantile.

A candidate must be derived from league rules, format, and a point-in-time player universe rather than one focal team's present roster composition. Selection should consider realized replacement-adjusted production, lineup opportunity error, stability across formats/positions, and uncertainty calibration. Freeze the chosen policy before evaluating each holdout fold.

## Time preference requires identification, not correlation

Transaction and pick evidence may reveal intertemporal economics, but a future-asset discount cannot be labeled time preference unless plausible confounders are addressed. At minimum study:

- age/career stage;
- current production;
- positional scarcity;
- asset liquidity;
- draft-class strength;
- pick-slot uncertainty where relevant;
- forecast uncertainty;
- contemporaneous market consensus as an explicit diagnostic rather than hidden target.

Estimate discounting only in training windows. Report sensitivity to controls and residual dependence on market consensus. If an apparently stable discount disappears or changes materially after confounder control, classify time preference as unidentified and retain a transparent benchmark weight rather than promoting the estimate.

## Intrinsic and market value must remain separable

For every chronological holdout, report:

- Pearson and rank correlation between intrinsic and market consensus;
- standardized residual disagreement;
- rate of material directional/value disagreement;
- examples where intrinsic materially disagrees with market and whether subsequent football economics support the disagreement;
- whether Market Value still adds incremental downstream information after Intrinsic Value is present.

High correlation is not automatically failure: both coordinates can respond to real football information. Failure occurs when intrinsic is effectively a market replica, cannot produce justified disagreement, or makes Market Value informationally redundant by construction.

## The simple model is a real candidate

Model A (transparent replacement-adjusted multi-year surplus) is eligible for promotion if it performs as well as or better than the hybrid challenger after accounting for uncertainty and stability. Model B must materially outperform Model A out-of-time to justify extra parameters or nonlinear structure. Complexity is a cost, not a tie-breaker in favor of the richer model.

## Economic usefulness is part of evaluation

Do not select models from aggregate prediction error alone. Predeclare cross-sectional and longitudinal scenario checks including:

- aging RB versus younger RB with comparable current production;
- elite QB longevity;
- developing WR;
- developing TE;
- league-format positional-scarcity changes, especially Superflex/1QB differences;
- expected appreciation/decline trajectories as new forecast seasons enter and older seasons roll off.

The expected direction should come from structural football economics and point-in-time Forecast evidence, not hardcoded player-age bonuses/penalties. Scenario failures require investigation even when aggregate loss improves.

## Uncertainty remains first-class

The final study must account for:

- annual Forecast uncertainty;
- career-transition multiplier dispersion and estimation error;
- uncertainty in estimated survival probabilities;
- cross-season dependence;
- replacement-threshold uncertainty;
- fitted discount/conversion parameter uncertainty;
- residual model uncertainty only where not already represented.

The preferred survival-probability treatment is Forecast-side bootstrap/posterior path sampling. Value must consume the resulting unconditional Forecast path distribution and must not reapply survival.

## Promotion gate

No production promotion unless the candidate:

1. beats the existing affine control out-of-time;
2. materially beats or justifies complexity relative to the transparent Model A;
3. generalizes across positions and league formats;
4. has defensible uncertainty coverage;
5. survives economic-usefulness scenario checks;
6. retains meaningful independence from Market Value;
7. passes anti-double-counting review;
8. uses only point-in-time-safe evidence with reproducible provenance.

If these conditions are not met, leave production intrinsic Value incomplete/fail-closed and report the no-promotion result.
