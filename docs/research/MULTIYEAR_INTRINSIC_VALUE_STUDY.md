# FSFFL NEXT Multi-Year Intrinsic Franchise Value Study

Status: research-only. No production authority is changed by this document.

## Purpose

Define and evaluate a multi-year intrinsic franchise-value model that remains meaningfully independent from current market value.

Intrinsic franchise value answers:

> What is the economic worth of the future football production and optionality an asset is expected to provide, relative to league-level replacement/scarcity, before considering the focal team’s specific needs and without treating current market sentiment as truth?

This is intentionally different from current market value, which describes observed/inferred exchange price. Market and intrinsic value remain separate decision dimensions.

## Non-goals and guardrails

The study must not:

- train intrinsic value to reproduce current market prices;
- use team-specific roster need, contender status, or strategic posture inside intrinsic economics;
- re-apply survival/attrition if Forecast already incorporated it into unconditional future production;
- collapse Market Value and Intrinsic Value into one master score;
- promote any challenger without strict chronological holdout evidence;
- use information that was not knowable at the historical as-of date.

League-level scarcity and opportunity cost may belong in intrinsic economics. Team-specific need remains downstream in Team Utility / Decision.

## Economic target

The target quantity is a distribution of **replacement-adjusted future football surplus expressed on a stable economic scale**.

For a player, the structural quantity begins with the annual sequence of point-in-time-safe Forecast distributions:

- season 1 expected production and uncertainty;
- season 2 expected production and uncertainty;
- ... through the supported horizon;
- attrition/survival already reflected in the unconditional Forecast distribution.

For each season, player production is compared against a league-context replacement/opportunity baseline for that position and lineup format. Only surplus above the relevant replacement baseline contributes positive intrinsic football surplus unless validation supports a bounded negative treatment for roster-consuming assets.

Future annual surplus is then weighted by an explicit time-value function. The resulting multi-year surplus distribution is converted to the intrinsic economic scale using parameters that may be structurally derived or empirically estimated as defined below.

The model is not intended to estimate what the market currently pays for the asset. It is intended to estimate the economic value of the football services and optionality expected from the asset.

## Parameter authority map

### Structurally derived

These parameters/behaviors should come from league rules, Forecast outputs, or transparent accounting rather than being fitted to market prices:

1. **Annual production path**
   - Source: Forecast-owned multi-year distributions.
   - Includes Forecast-owned career transition and attrition treatment.

2. **Lineup-format demand**
   - Source: league rules: team count, required QB/RB/WR/TE/FLEX/SUPERFLEX slots, roster structure.
   - Purpose: determine league-level demand for playable production by position.

3. **Replacement population definition**
   - Source: league rules plus the point-in-time player/forecast universe.
   - Must be defined before outcome fitting and versioned.
   - Must not use the focal team’s own roster deficiencies.

4. **No double application of survival**
   - Source: Forecast contract.
   - Forecast multi-year distributions are unconditional when survival has already been applied.

5. **Economic separation from Market Value**
   - Market price may be calibration/validation evidence for selected parameters but cannot be the direct prediction target of the intrinsic model.

### Empirically estimated candidates

These parameters may be fitted if point-in-time-safe evidence supports them:

1. **Future-season discount/time-value function**
   - Candidate forms: exponential, hyperbolic, piecewise annual weights.
   - Primary fitting evidence should come from revealed intertemporal exchange behavior where future-vs-current football production is identified without simply minimizing error to market player values.
   - Examples: pick-for-player and age/production trade substitutions, historical transactions, and draft-capital exchanges after controlling for current production and uncertainty.

2. **Replacement/opportunity threshold within the structurally defined replacement population**
   - Candidate examples: marginal starter, first bench replacement, replacement quantile by position.
   - Fit/choose using predictive performance for realized lineup utility and transaction indifference, not current cross-sectional market-price reproduction alone.

3. **Economic conversion from replacement-adjusted multi-year surplus to intrinsic value units**
   - Fit against outcome-relevant or transaction-indifference evidence where possible.
   - Market prices can be one external anchor but cannot be the sole dependent variable.

4. **Optionality/nonlinearity above elite surplus levels**
   - Challenger only.
   - Must be evidence-supported and interpretable; e.g., diminishing or increasing marginal value of elite surplus due to lineup constraints/scarcity.

5. **Residual intrinsic uncertainty**
   - Estimated from historical forecast-to-realized football outcome error and model residuals after structural uncertainty propagation.

## Evidence roles

### Fitting evidence

Preferred fitting evidence, in descending conceptual priority:

1. Point-in-time historical Forecast inputs and subsequent realized football outcomes for production/replacement calibration.
2. Historical league-rule-aware lineup outcomes for testing replacement/opportunity baselines.
3. Point-in-time completed dynasty transactions that identify intertemporal tradeoffs or relative economic indifference, especially where current-production differences can be controlled.
4. Historical draft-pick exchanges and pick outcomes for future-value timing evidence.
5. Current/historical market-value sources only as a constrained anchor or auxiliary feature where justified, never as the sole target.

Every fitting row must preserve an as-of timestamp, source/provenance, league/format context where relevant, and an evidence cutoff.

### Validation-only evidence

At least one evidence family must remain validation-only for each study version. Candidates include:

- a held-out market source not used in fitting;
- held-out league transaction history;
- future seasons after the chronological split;
- realized downstream team/lineup outcomes;
- rank-order or package-consistency checks against external dynasty markets.

Market evidence is especially useful here: a strong intrinsic model need not equal market price, but unexplained, persistent, out-of-time divergences should be diagnosable rather than ignored.

## League-level positional scarcity / replacement value

The default candidate definition is league-structural rather than team-specific.

For each historical league/as-of state:

1. Read lineup rules and team count.
2. Build the point-in-time eligible player universe and their point-in-time forecast distributions.
3. Determine structurally demanded starting slots by actual position, accounting for FLEX/SUPERFLEX eligibility.
4. Optimize league-wide starting assignments or otherwise estimate the marginal player consumed by the league’s starting demand.
5. Define replacement as a predeclared margin beyond starting demand (candidate policies should be studied rather than hidden):
   - marginal starter;
   - first readily available bench replacement;
   - replacement quantile beyond starter demand.
6. Estimate annual replacement production by position from that point-in-time universe.

The replacement definition is common to all teams in the same league context. A team being desperate for RB does not raise intrinsic RB value; that team-specific effect belongs in Team Utility / Decision.

Candidate replacement policies must be compared chronologically and frozen before holdout evaluation.

## Future-season weighting / discounting

No arbitrary discount rate should be promoted.

Candidate study set:

1. **Transparent discounted-surplus baseline**
   - Fixed, predeclared annual weights used only as a benchmark.
   - Example families may be tested over a bounded grid, but the selected baseline must be chosen on training data only.

2. **Hybrid structural model**
   - Estimate a parsimonious time-value function from point-in-time historical evidence of intertemporal asset exchange and/or realized economic usefulness.
   - Prefer one or very few interpretable parameters.
   - Fit within training windows; freeze before chronological holdout.

3. **Existing affine control**
   - Existing `ForecastValueMapping` mechanics using one forecast distribution and an affine economic conversion.
   - Treat as control/scaffold, not assumed truth.

Discounting applies to future **surplus economics**, not to already-discounted market prices. Avoid importing market time preference twice.

## Uncertainty propagation

The model must publish an intrinsic-value distribution, not just a point estimate.

### Forecast uncertainty

Use Forecast-owned annual distributions without mutation.

### Survival / attrition

If Forecast has already built unconditional distributions with survival probability applied, Value must not multiply by survival again.

However, current Forecast career calibration records `survival_standard_error` but the present multi-year propagation does not explicitly carry uncertainty in the estimated survival probability itself. This study should evaluate a Forecast-side challenger that propagates parameter uncertainty in survival, preferably through hierarchical/posterior or bootstrap sampling, while preserving the Forecast → Value authority boundary.

Value should consume the improved Forecast distribution if that challenger is separately validated and promoted. Value should not independently re-estimate survival.

### Cross-season dependence

Annual outcomes are not independent. Career survival, role persistence, injuries, and talent shocks create correlated paths.

The research model should compare:

- an independence approximation as a transparent baseline;
- path-based Monte Carlo using shared latent career states or bootstrap career trajectories where evidence permits.

### Replacement uncertainty

Replacement production should also be treated as estimated, with uncertainty from the point-in-time player population and forecast errors.

### Parameter-estimation uncertainty

Discount, conversion, and other fitted coefficients should carry uncertainty from the training sample. Bootstrap or posterior draws are preferred over pretending fitted coefficients are exact.

### Residual model uncertainty

Residual intrinsic uncertainty should be additive only for uncertainty not already represented by Forecast, replacement, path, and parameter distributions. Anti-double-counting tests are required.

## Challenger models

### Model A — transparent replacement-adjusted surplus baseline

Purpose: strong interpretable benchmark.

Inputs:
- annual Forecast distributions;
- league-structural replacement production by position;
- fixed/predeclared future-season weights;
- simple scale normalization.

No current market price as target.

### Model B — hybrid structural + empirical intrinsic model

Purpose: candidate authority replacement.

Same structural inputs as Model A, but selected parameters are estimated from point-in-time-safe historical evidence:
- time-value/discount function;
- replacement margin policy if evidence supports selection;
- economic conversion/normalization;
- any bounded nonlinear surplus transformation.

Market and transaction evidence may inform parameters but the objective must include independent outcome/economic criteria and must not reduce to current-market replication.

### Model C — existing affine control

Current `ForecastValueMapping` form:

`intrinsic = intercept + slope * forecast production`

Use the best point-in-time-safe implementation possible for comparison. This is the control, not the presumed incumbent authority.

## Chronological evaluation design

All model selection must use strict chronology.

1. Build historical point-in-time rows with evidence available at each as-of date only.
2. Choose one or more expanding/rolling training windows.
3. Fit every empirical parameter on training data only.
4. Freeze model and parameters.
5. Evaluate on the next chronological holdout block.
6. Roll forward and repeat.
7. Aggregate holdout performance only after all folds are complete.

No random train/test split is sufficient for promotion.

## Evaluation criteria

Because intrinsic value is intentionally not market price, no single market-price error metric can determine promotion.

Evaluate at least four families:

1. **Football-economic validity**
   - realized replacement-adjusted production captured;
   - long-horizon calibration of expected surplus;
   - uncertainty coverage / calibration.

2. **Intertemporal economic validity**
   - ability to explain held-out future-vs-current asset exchange relationships;
   - consistency of inferred discounting across eras/formats.

3. **Decision usefulness**
   - held-out trade cases where near-term, market, and intrinsic dimensions disagree;
   - whether intrinsic direction better predicts subsequent franchise football surplus than the affine control/baseline.

4. **Independence from current market value**
   - correlation and residual analysis versus market price;
   - demonstrate that the model can materially disagree with market when football economics support it;
   - test whether adding current market value as a separate downstream dimension still contributes information. If intrinsic merely reproduces market, the challenger fails this guardrail.

## Promotion standard

Model B may replace the affine scaffold only if it:

- materially outperforms Model C out-of-time on football-economic and intertemporal criteria;
- materially improves on Model A enough to justify added complexity;
- produces calibrated uncertainty or clearly better coverage/error diagnostics;
- remains interpretable and attributable to a small set of governed parameters;
- preserves meaningful informational independence from Market Value;
- passes anti-double-counting review;
- passes sensitivity/stability checks across position and league format;
- has reproducible provenance and fit metadata;
- does not rely on hindsight-contaminated inputs.

If those standards are not met, production remains unchanged.

## Required research outputs before any promotion PR

1. Historical evidence inventory and rights/provenance matrix.
2. Explicit replacement-policy study.
3. Discount/time-value estimation study.
4. Survival-uncertainty propagation study owned by Forecast research.
5. Three-model chronological benchmark report.
6. Independence-from-market diagnostic.
7. Position/format stratification report.
8. Parameter sensitivity and stability report.
9. Written promotion/no-promotion recommendation with evidence.

## Immediate implementation sequence

1. Inventory existing historical Forecast, transaction, pick, market, and realized-outcome evidence in the repository.
2. Define a point-in-time `IntrinsicCalibrationRow` research contract without changing production Value authority.
3. Build Model A as research-only code.
4. Reconstruct the best point-in-time-safe affine Model C control.
5. Add chronological benchmark harness shared by A/B/C.
6. Fit only the minimum interpretable parameters needed for Model B.
7. Run strict holdouts and diagnostics.
8. Stop with a research report unless the promotion standard is clearly satisfied.
