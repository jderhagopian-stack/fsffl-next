# Intrinsic magnitude presentation v1

Version: `intrinsic-magnitude-v1:linear-fixed-20261108`.

## Decision and authority

User directs completing PR #464's display work through deployment using historical actuals for scale diagnostics. Historical forecast-provider vintages are not a blanket prerequisite for this presentation change. This supersedes the earlier proposed release blocker; it does not reclassify historical outcomes as forecasts or approve changes to accepted raw models.

Use PR #464's leading **linear** family, with fixed reference raw units **750 for 3-Year** and **2200 for Career**, in the supported FSFFL half-PPR scoring and lineup-capacity economy. References are governed display benchmarks, not estimated absolute ceilings or claims that forecast accuracy has been newly validated. Do not refit them on each player population, roster query or refresh. A changed reference requires a new version and review.

```
index = 10000 * clamp(raw / reference_raw, 0, 1)
```

Positive uncapped contributions retain their raw ratios and gap proportions within each horizon. Missing or nonfinite values display unavailable; negative raw displays zero while the signed raw remains intact. Above-reference values display `10,000+`, retain native raw, and expose an overflow flag. Zero maps to zero. Ties in raw remain ties.

3-Year retains Value's accepted discounted Y1–Y3 Shapley contribution. Career retains undiscounted Y1–Y7 plus the accepted Y8+ tail. No age, Market or display-index blend enters either quantity. A point in one horizon does not equal a point in another or a Market point. Percentile ranks remain separately available; Market disagreement uses percentile ranks rather than subtracting independent display scores. Decision/package economics and Position & Depth consume existing raw authorities unchanged.

## Format boundary

Use the existing Foundation 4 player-offense scoring compatibility contract and lineup-capacity signature `a4d9a532c477b9fb2114a33009b94adbe15823748efec46d9701bdcddc8f5363`. Semantically equivalent provider ordering and inert rules are permitted through those existing contracts. Other formats retain their existing explicit presentation coordinate; they do not borrow the new references or lose existing coverage. The resolver cache is bounded to 32 rule/horizon keys.

## Evidence and limitations

PR #464 exact research head `8a3d8295785fc7465578294a17b0dcad7d728769`; baseline main `e0e045a44b4c5b19061922995b1a49d3347c91d2`. User-supplied archive hashes all verify. Corrected historical results match the current production Shapley engine exactly across **22,488 cohort-player-year entries**, preserving **11,611 nulls**. Observed annual pools span 2003–2022 (11,528 season-player observations), at 2048 permutations and seed 20260915. Five starting cohorts: 2003, 2006, 2009, 2012, 2015.

There are **1623** continuously observed complete three-year windows. Illustrative 12-team 2WR Superflex: **one** exceeds 750 (**0.0616%**), max 753.639448 (overflow **0.4853%** of reference). Removing Superflex: none exceeds 750, max 697.518014. These are retrospective, partly overlapping, survival-selected windows and an illustrative format, not untouched prospective holdouts or calibration for every league. Their purpose is inspecting ruler behavior, including explicit overflow. They are not historical forecast accuracy tests.

Canonical Career artifact 12991 and final lens surface 12999 reconcile all **367** players: raw Career exactly; reconstructed discounted three-year max delta **1.14e-13** from summation order. Current maxima: raw 3-Year **722.965905**, Career **2062.767304**; neither benchmark clips a current player. Current November evidence is subsequent to the October reference hypotheses; all saved native Career records still evaluate 2026, so no multi-season native Career validation is claimed.

Career tail remains the accepted `career-tail-two-family-v1:fsffl-connected-scoring-recalibration-v1` coarse/set-valued authority, with original supported families, provenance, holdout results and uncertainty. Its packaged 2011 holdout has 526 scored rows; combined outer-90 coverage **0.9258555**, outer-80 **0.6064639**. Those are existing tail evidence, not newly achieved whole-Career calibration or grounds to suppress uncertainty. Seven-year hindsight values exclude Y8+ and cannot establish a Career ceiling.

## Integration and historical integrity

One pure presentation module owns references/formula/version. Current persisted lens surfaces can be projected from their saved raw quantities without database writes, new model work, provider acquisition or intelligence refresh. Projection occurs only after existing persistence identity/integrity validation. Stored historical payloads/hashes remain unchanged; stale last-good surfaces retain their original coordinate rather than borrowing a newer State's rules. Newly promoted matching-state nested Intrinsic metadata receives the publication owner's final generation ID.

Franchise, Player Intelligence, Explore, League comparison and Trade-facing display use the same supported mapping. Player Intelligence consumes Career's exact-State Y1–Y3 components to match roster/Explore rather than substituting a different Current cohort's raw scalar. Raw snapshots, coverage and scoring/source rules remain unchanged.
