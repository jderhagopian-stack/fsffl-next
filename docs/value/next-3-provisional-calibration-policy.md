# NEXT-3 Provisional Calibration Policy

NEXT-3 distinguishes a real economic effect from confidence in its current coefficient. Incomplete evidence must not become hidden hardcoding, but it also must not be mistaken for evidence that the effect is zero.

## General rule

A provisional calibration is permitted only when all of the following are true:

1. the economic effect is structurally or empirically plausible and belongs in NEXT-3;
2. available evidence is insufficient for authoritative promotion;
3. the provisional behavior is explicit, versioned, bounded, uncertainty-aware, and replaceable;
4. downstream consumers can identify that the estimate is provisional or unavailable;
5. no second module re-adds the same effect.

A missing calibration must never be silently replaced by a different value concept. In particular, market price is not an implicit substitute for intrinsic value, and market price is not an implicit transaction price.

## Market price

Status: **AUTHORITATIVE method**.

The default broad-market estimator is the robust median across compatible independent evidence roots. No learned provider weights are authoritative yet. If source lineage is ambiguous or partially overlapping, the estimator fails closed rather than fabricating fractional independence.

If fewer than the required number of independent evidence roots are available, the market estimate is unavailable for that requested confidence level. A caller may explicitly request a thinner baseline, but that choice must be visible in its model/version metadata.

## Format and league market context

Status: **AUTHORITATIVE machinery; provisional learned shrinkage strength where evidence is thin**.

The hierarchy is:

`global market -> format cohort -> league residual`

A new or low-data league remains close to its broader cohort because its empirical residual has low weight. This is not a hardcoded league premium. As transactions accumulate, the league residual and its uncertainty update.

Structural scarcity implied by league rules is not re-added through league market residuals.

## Forecast-to-intrinsic conversion

Status: **PROVISIONAL_GOVERNED coefficients until a chronological fit is promoted**.

`ForecastValueMapping` remains an explicit required input. NEXT-3 contains no universal fallback slope or intercept. A mapping used operationally must record model version, upstream forecast-model version when applicable, evidence-through season, sample size, and residual uncertainty.

If no governed mapping exists for the requested forecast/context, the intrinsic estimate is **unavailable**. The caller must not substitute the market estimate and relabel it intrinsic.

This preserves the distinction between football-derived economic worth and observed exchange price while allowing better mappings to be promoted later without redesign.

## Pick value

Status: **AUTHORITATIVE mixture architecture; PROVISIONAL_GOVERNED empirical outcome sets until promoted**.

A pick value must be produced from an explicit probability distribution over possible slot/outcome states. Exact slot, unresolved slot, class-strength, and horizon uncertainty are evidence inputs rather than embedded multipliers.

Published external pick curves may be used as market comparators or research evidence, but they are not automatically treated as realized-outcome truth. If an empirically supported `PickOutcomeSet` is unavailable for a requested context, NEXT-3 must not invent early/mid/late coefficients.

## Transaction price and liquidity

Status: **AUTHORITATIVE representation; PROVISIONAL_GOVERNED coefficients**.

`TransactionPriceMapping` remains an explicit required input. There is no universal hidden acquire premium, sale discount, or liquidity haircut.

Clean one-for-one trades are used first as pairwise clearing evidence. Multi-asset packages remain packages and may not be decomposed into unsupported scalar per-asset prices. Until a broad transaction corpus supports directional offsets, a transaction-price estimate is unavailable unless a governed context-specific mapping is supplied.

This does not assert that transaction friction is zero. It asserts that NEXT-3 will not encode an unsupported mean effect while evidence is still being assembled.

## Uncertainty

Uncertainty is never removed merely because a mean coefficient is provisional. NEXT-2 forecast uncertainty, market-source disagreement, pick-outcome dispersion, league-residual uncertainty, and transaction residual uncertainty remain distinct and enter their authoritative concept once.

Where a residual distribution is not supported, NEXT-3 may carry mean/variance while leaving quantiles unset rather than inventing a distributional shape.

## NEXT-4 consumption rule

NEXT-4 may consume:

- authoritative NEXT-3 estimates;
- explicitly governed provisional estimates supplied with their calibration/version metadata;
- absence of a value concept as an explicit state.

NEXT-4 may not:

- relabel market price as intrinsic value;
- infer transaction premiums on its own;
- create pick-value curves;
- re-add league scarcity already represented by NEXT-3;
- promote a challenger simply because an authoritative estimate is unavailable.

This policy allows NEXT-4 development to proceed while NEXT-3 empirical parameters continue to improve over time, without compromising authority boundaries or forcing arbitrary coefficients into production.