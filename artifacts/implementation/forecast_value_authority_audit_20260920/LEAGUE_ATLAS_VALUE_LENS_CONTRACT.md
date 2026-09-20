# League Atlas Value-Lens Contract

## Decision

The upcoming League Atlas should expose **Broad Market** and **FSFFL Intrinsic** as two parallel player-level lenses.

It must not collapse them into one value score.

## Broad Market lens

Source:
- current `CurrentMarketValueRuntimeResult.estimates`
- scale `dynasty-market-percentile`

Meaning:
- where the broader dynasty market prices a player relative to the market population.

Allowed Atlas uses:
- player color/marker;
- position-by-position visual comparison;
- hover/tap exact percentile;
- disagreement overlay against Intrinsic percentile.

Forbidden:
- summing player percentiles into team Market Value;
- calling a team percentile sum “League Market Value”;
- using Broad Market as a fallback Intrinsic value.

## FSFFL Intrinsic lens

Source:
- current governed Shapley Intrinsic contract
- raw quantity `raw_governed_shapley_marginal_fantasy_points`

Atlas display coordinate:
- percentile rank of raw Intrinsic within the governed Intrinsic population.

Meaning:
- where FSFFL football economics rank the player, independently of market price.

Allowed:
- player color/marker;
- position/team distribution;
- exact presentation percentile;
- disagreement overlay against Broad Market percentile.

Forbidden:
- raw subtraction from Broad Market;
- summing percentile ranks into a team Intrinsic total;
- turning the lens into Team Utility;
- creating action authority from disagreement.

## Team grouping

The new `/api/league/value-lenses` contract groups rostered player identities by team and reports coverage counts only.

It intentionally creates:
- no team value total;
- no team value rank;
- no League Market Value;
- no Team Utility;
- no acceptance probability;
- no recommendation.

This gives the Atlas enough structure to draw player-level market/economics maps while preserving the authority boundary.

## How Atlas should combine the lenses visually

Recommended visual grammar:
- lens toggle: **Broad Market | FSFFL Intrinsic | Difference**
- Broad Market and Intrinsic use the same 0–100 percentile visual axis only for presentation;
- Difference is `Intrinsic percentile - Broad Market percentile`;
- hover/tap always names both original lenses;
- no “winner,” buy/sell command, or common raw scale.

At team level, the first implementation should show the player distribution inside each roster/position, not a single team score.

If management later wants a team-level market or intrinsic value coordinate, that requires a separate Value-layer promotion with its own additive semantics and validation. Presentation must not invent it.

## Relationship to existing Team Utility

The Atlas may continue to show already-authoritative competitive lanes, position strength, expected wins, probabilities, and fragility from Team Utility as **separate structural layers**.

Broad Market and Intrinsic do not feed or alter those Team Utility calculations.

The phrase “do not create Team Utility prematurely” means the Value lenses must not be aggregated into a new roster-fit/competitive score in Presentation. Existing Team Utility evidence remains valid and separate.
