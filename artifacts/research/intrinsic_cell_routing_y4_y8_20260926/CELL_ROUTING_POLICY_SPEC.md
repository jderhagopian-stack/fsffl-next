# Cell-Specific Long-Horizon Routing / Shrinkage Policy Freeze

Date: 2026-09-26  
State: **FROZEN BEFORE REPEATED OUTER VALIDATION**

This corrective does not repair the already-seen holdout by hand. It defines a general routing and shrinkage procedure before the new repeated rolling-origin evaluation is scored.

## Candidate universe

The model search itself is not restarted.

For each position × horizon cell, the candidate set is the five best specialist candidates from the already-completed **development-only** model matrix, plus the incumbent comparator when it was not already among those five.

The development-selected shared anchor is also eligible:
`global_continuous|football_plus|two_part_ridge`.

This makes the incumbent one candidate among others. It receives no automatic authority because the prior blanket architecture failed elsewhere.

## Repeated rolling-origin contract

For every horizon:
- evaluate the latest **up to five** eligible historical origins;
- require at least two outer origins to run a repeated-validation diagnostic, but require at least **three** outer origins before any exact-cardinal cell route can be supported;
- require at least three earlier eligible origins before an outer origin can be scored;
- when a deep horizon has fewer than five defensible outer origins, use all available qualifying origins rather than fabricate or relax chronology;
- Y8 has only five eligible origins total (2014-2018); preserving three earlier origins leaves two outer tests (2017-2018), so Y8 cannot earn exact-cardinal routing authority in this corrective regardless of those two outcomes;
- use at most the five most recent earlier origins for route selection;
- for outer origin T, every fitted training row must satisfy `target_season < T`;
- route selection for T may use only earlier evaluation origins U<T.

The already-exposed comprehensive final holdout is not read by this workflow. Some of those historical years can naturally appear as rolling outer origins, but they are treated only as part of a predeclared repeated historical validation sequence and are not relabeled as untouched.

## Policies evaluated

1. **Baseline comparator** — `specialist|forecast10|two_part_ridge`.
2. **Previously rejected blanket 75/25 comparator** — preserved exactly for diagnostic comparison.
3. **Hard cell router** — choose the candidate with the best permitted inner multi-objective score.
4. **Soft cell stack** — shrink across the top three permitted candidates using deterministic exponential weights from inner evidence.

The soft stack has no privileged baseline anchor. The incumbent, richer specialists and the shared anchor compete under the same score.

## Multi-objective selection loss

Within each cell and permitted inner window, candidate metrics are normalized to the **median candidate** rather than to the incumbent.

Weights preserve the comprehensive study's priorities:
- RMSE 0.32;
- MAE 0.16;
- top-tail RMSE 0.22;
- Spearman ordering 0.15;
- absolute bias 0.05;
- plus the already-governed model/feature/architecture complexity penalty.

## Cell interpretation

The output is allowed to say:
- a richer/specialized candidate is supported;
- the incumbent comparator is supported;
- multiple candidates are effectively indistinguishable and shrinkage is preferred;
- exact cardinal precision is not supported and the cell should remain coarse/uncertain.

No single failed cell may grant the incumbent authority over the other cells.

## Guards

The routing workflow must not consume:
- the prior final-holdout prediction or metric artifacts for selection/tuning;
- current named-player shadows;
- Market, dynasty value, Owner Intelligence or Team Utility.

Production H3 remains unchanged.
