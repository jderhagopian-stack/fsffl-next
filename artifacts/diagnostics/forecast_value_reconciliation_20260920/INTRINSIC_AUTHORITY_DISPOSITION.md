# Intrinsic authority reconciliation and Franchise migration disposition

Date: 2026-09-20

## Current distinct Intrinsic coordinates

### Legacy `/api/value/intrinsic-v1`

Model:
- `intrinsic-value-v1`
- scale: `fsffl_intrinsic_surplus`
- unit: weighted expected fantasy-point surplus above replacement

Economics:
1. construct a governed three-year Forecast path;
2. derive league-lineup replacement distributions;
3. at each horizon compute max(0, player_mean - replacement_mean);
4. weight Y1 / Y2 / Y3 by 1.00 / 0.85 / 0.70;
5. sum weighted surplus.

This is a replacement-adjusted surplus coordinate.

### Current `/api/value/intrinsic-shapley-v1`

Model family:
- `intrinsic-shapley-i1-v1`
- raw quantity: governed Shapley marginal fantasy-point contribution

Economics:
1. consume the governed Y1/Y2/Y3 Forecast path;
2. define a lineup-capacity deployment game from league rules;
3. estimate each player's marginal contribution over frozen random permutations;
4. for future horizons integrate state-conditioned marginal contributions;
5. discount future Shapley contributions at the frozen annual discount.

This is a deployment-attribution coordinate.

Market, owner, trade and Team Utility inputs do not enter the Shapley calculation.

## Semantic comparison

The two coordinates are related because both consume Forecast and reflect scarce lineup opportunity. They are **not algebraically or economically identical**.

Legacy Intrinsic v1 asks: How much expected fantasy-point surplus does this player create above a position/lineup replacement benchmark over three weighted years?

Shapley Intrinsic asks: How much marginal deployment value is attributable to this player in the governed lineup-capacity game across current and future Forecast states?

Differences include:
- replacement construction versus coalition/deployment attribution;
- horizon weights 1.00/0.85/0.70 versus annual Shapley discount 1/0.85/0.85²;
- direct surplus floor versus permutation-based marginal contribution;
- different output semantics and version/provenance contracts.

Therefore endpoint substitution is **not semantic/parity-safe presentation wiring**.

## Current consumers

Legacy Intrinsic v1:
- Franchise/My Team Value Lens still calls `/api/value/intrinsic-v1`.

Shapley Intrinsic:
- Market-vs-Intrinsic disagreement discovery;
- `/api/league/value-lenses`;
- current Atlas-safe comparison contract;
- versioned future Forecast/Shapley implementation path.

## Directive disposition

The implementation directive permits a bounded Franchise migration only if Shapley is already canonical presentation authority **and** migration preserves economic meaning/parity.

That condition is not met.

**Disposition: DO NOT migrate the Franchise Value Lens endpoint in PR #162.**

This is a hard-stop management decision, not an implementation omission. Replacing the endpoint would change the economic question shown to the user.

## Recommended management choice

Management should explicitly choose one of these future paths:

1. **Retire legacy Intrinsic v1 from product presentation** and redesign the Franchise lens around Shapley semantics, accepting that this is a product/economic-coordinate migration rather than parity wiring; or
2. **Retain both coordinates** with distinct names/questions if both economic views are useful.

PR #162 should not choose between those product/economic semantics implicitly.

## Atlas implication

Until management decides otherwise:
- the Atlas comparison authority is **Broad Market vs Shapley Intrinsic** at player-level percentile/rank presentation coordinates;
- legacy Intrinsic v1 does not feed the Atlas;
- Cardinal remains a separately named optional market-cardinal/accounting coordinate and does not replace either lens;
- no team Intrinsic total, League Market Value, or new Team Utility score is created.
