# League Atlas v1 — authority inventory

Date: 2026-09-21
Base main: `c914e154b7b7819ccf265bdbf63dc22795fe31b8`

## Product objective

Build a scan-first League surface that lets an owner understand how franchises differ before drilling into exact evidence. Presentation organizes governed truth; it does not create a master score, a new Value coordinate, acceptance probability, or recommendation authority.

## Visual-to-authority map

| Atlas concept | v1 visual | Governed source | Authority | v1 status |
| --- | --- | --- | --- | --- |
| Positional monopolies / weak rooms | heat-map / rank cells at QB, RB, WR, TE | `/api/league/team-views` → `TeamAnalyticsView.position_strengths` | Team Utility diagnostic built from governed optimized Forecast production | available |
| Competitive identity | contender / competitive / developing / rebuilding lanes | `TeamUtilityVector.calculated_competitive_state` plus existing competitive outcome evidence | Team Utility / Simulation | available where current evidence exists |
| Age profile | compact young-to-old comparison using roster and projected-starter ages | `TeamAnalyticsView.roster_average_age`, `starter_average_age`, coverage counts | Analytics over canonical point-in-time State ages | available with missing-age coverage |
| Pick wealth | owned-pick inventory bars/counts | `TeamAnalyticsView.draft_picks` from canonical State ownership | State / Analytics | available |
| Depth / fragility | expandable resilience band | `TeamUtilityVector.roster_resilience` | Team Utility | available where Forecast coverage supports it |
| Broad Market | player-distribution strip / exact player drill-down | `/api/league/value-lenses` → `broad_market_percentile` | Value — Broad Market percentile | available independently |
| FSFFL Intrinsic | player-distribution strip / exact player drill-down | `/api/league/value-lenses` → Shapley-derived `intrinsic_percentile` | Value — canonical Shapley Intrinsic, presentation percentile only | available independently |
| Market vs Intrinsic disagreement | player-distribution strip / exact player drill-down | `percentile_gap = intrinsic percentile - Broad Market percentile` from governed value-lens contract | Presentation coordinate explicitly authorized by Value contract | available only when both lenses exist |
| Trade-partner context | handoff from positional supply / pressure point to Market | existing descriptive position supply only | Presentation handoff; no Search/Decision fit created here | descriptive only |
| Exact evidence / provenance | expandable definitions and per-player tap detail | existing model/version/status fields and route contract | originating layer | available |

## Explicitly unavailable / deferred in v1

The Atlas will not create or imply:
- team FSFFL Intrinsic totals or ranks;
- summed Broad Market percentiles;
- League Market Value;
- owner-adjusted universal Value;
- a universal team value score;
- hidden composite power grades;
- numeric acceptance probability;
- recommendation strength;
- trade-partner fit unless an existing Search/Decision contract explicitly supplies it;
- Forecast-vNext A2 output or promotion.

## Composition decision

No new model layer is required for this slice. Existing contracts already provide the needed governed evidence:
- `/api/league/team-views` for State / Forecast / Analytics / Team Utility structure;
- `/api/league/value-lenses` for Broad Market / Shapley Intrinsic / percentile-gap player lenses.

The bounded v1 work should therefore remain presentation-heavy:
1. replace the current optional Cardinal-team-value dependency on the League page with the governed value-lens contract;
2. show player-level value distributions rather than team value totals;
3. keep pick wealth descriptive and State-owned;
4. preserve unavailable/degraded states;
5. retain progressive drill-down and mobile scan behavior.
