# Current Ranking Authority Ledger

Date: 2026-09-20

This ledger records the authority behind visible ordering/ranking. No presentation rank below creates a new universal score.

## Player / asset rankings

| Surface / ranking | Exact driver | Authority family | Notes |
| --- | --- | --- | --- |
| NFL season projection | season `fantasy_points` Forecast mean | Forecast | multi-provider live Forecast; product display helper selects season horizon |
| projection rank at position | descending displayed NFL season projection among same-position league players | Forecast + Presentation ordering | no Value input |
| FSFFL Cardinal Value player rank | descending `FSFFLCardinalValueScore.score` | Value — market-cardinal | authoritative player Cardinal uses format-locked Stats Guy 0–10,000 reference cohort |
| Players & Assets default sort | FSFFL Cardinal Value descending | Value — market-cardinal | previously labeled generic FSFFL Value; this branch makes the label explicit |
| highest-value Franchise core / optionality | FSFFL Cardinal Value descending | Value — market-cardinal | not Intrinsic |
| Broad Market percentile | multi-source `dynasty-market-percentile` estimate | Value — Broad Market | provider-native values become within-source percentiles; governed market estimator combines source evidence |
| Market-vs-Intrinsic disagreement ordering | absolute difference between Broad Market percentile and Shapley Intrinsic presentation percentile | Presentation/discovery only | raw values are never subtracted; no recommendation authority |
| Franchise Value Lens on current main | older `/api/value/intrinsic-v1` Model-A coordinate | legacy Intrinsic v1 compatibility surface | **not the Shapley contract used by Market disagreement; do not feed this legacy endpoint into League Atlas** |

## Team / franchise rankings and orderings

| Surface / ranking | Exact driver | Authority family | Notes |
| --- | --- | --- | --- |
| QB/RB/WR/TE league rank | optimized starter expected points at actual position | Team Utility descriptive diagnostic built from Forecast-backed optimized lineup | 100 index = league-average position production; no composite team grade |
| optimized projected scoring rank | optimized lineup fantasy-regular-season points | Forecast / lineup analytics | named metric only |
| expected wins rank | Simulation competitive outcome expected wins | Simulation / Team Utility competitive outcome | named metric |
| playoff / first-place / championship rank | matching Simulation probability | Simulation / Team Utility competitive outcome | each ranked independently |
| competitive-state lanes | calculated competitive state policy | Team Utility | not owner posture |
| fragility rank | largest single-player lineup drop, lower is better | Team Utility resilience | named metric only |
| draft-pick count rank/order | raw owned-pick count | State / Analytics | no pick-value economics implied |
| League age ordering | canonical point-in-time player ages | State / Analytics | descriptive; missing ages are not imputed |
| League asset-structure row order | owned pick count descending | State / Presentation | FSFFL Cardinal totals are displayed but do not drive this row order |
| FSFFL Cardinal team comparison | sum of additive FSFFL Cardinal player/pick scores | Value — market-cardinal accounting | explicitly not Broad Market Value, Intrinsic, Team Utility, or Decision |
| Total Market Value | **unavailable** | Value | Broad Market percentile is non-additive; code fails closed instead of summing it |
| legacy Analytics `asset_portfolio_mean` | imported `utility.asset_portfolio` when present | upstream Value imported into Team Utility vector | current baseline simulation assembly does not attach an asset portfolio; do not use as Atlas Value authority |

## Important naming finding

Current main contains an ambiguous presentation alias: the `total_cardinal_value` metric can be relabeled **“Franchise value.”** That makes a market-cardinal accounting coordinate sound like a universal franchise-value or Intrinsic ranking.

This branch removes that alias and labels the coordinate **FSFFL Cardinal Value** explicitly.

## Intrinsic authority finding

Two Intrinsic implementations remain present in the repository:
1. legacy `/api/value/intrinsic-v1` — replacement-adjusted Model A compatibility surface;
2. current Shapley contract `/api/value/intrinsic-shapley-v1` — the governed contract used by the latest Market disagreement work and future-Forecast/P0 authority.

The upcoming League Atlas contract in this branch uses the **Shapley Intrinsic contract**, not the legacy Intrinsic-v1 endpoint. The legacy Franchise Value Lens is therefore a known presentation migration item and must not silently define Atlas authority.
