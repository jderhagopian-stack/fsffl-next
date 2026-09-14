# Latest Intrinsic Result — Forecast Career-State Calibration

## Decision

**KEEP A AS TEMPORARY INCUMBENT. Do not promote repaired Forecast states + D2. Do not merge PR #138.**

This workstream kept A/B/C/D/D2 frozen and changed only Forecast-owned career-state research. The explicit-state concept remains sound: D2 still prevents generic Forecast variance from becoming free dynasty option value. The attempted Forecast repair, however, does not make D2 competitive with A.

## Exact research state

- main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- Forecast calibration evidence head: `029f4e5ba6ac0308981e9d990f59f411840ddb7c`
- PR #138 remains open/unmerged
- PR #137 remains superseded/unmerged
- unresolved review threads at the last exact check: 0

## What was calibrated

A governed Forecast contract now exists for player/horizon career-state distributions, including state probabilities, upward/downward transition probability, survival, state-conditioned production, confidence/evidence quality, model version and provenance.

Three bounded six-state taxonomy constructions were tested chronologically: existing-style k-means production states, balanced quantiles and starter-tail quantiles. K-means was least bad; none earned production promotion.

Transitions used chronological historical football evidence only: position, current state, age, experience and draft-capital tier with hierarchical shrinkage. Existing governed QB meaningful-starter probabilities were retained rather than rebuilt.

## Calibration result

There are two important views of the evidence.

**When both current and future states are defined from realized historical production**, the research transition model calibrates fairly well on 7,072 observations:

- upward: **20.7% predicted vs 19.0% realized**
- downward: **47.9% vs 49.7%**
- persistence: **31.4% vs 31.2%**
- Brier: **0.1164**
- log loss: **1.4537**

But that is not the coordinate D2 actually consumes. D2 must infer current state from the **Forecast Y1 mean**. On the inference-aligned population (4,102 observations), the same model is badly biased:

- upward: **21.8% predicted vs 36.3% realized**
- downward: **49.1% predicted vs 29.2% realized**
- persistence: **29.1% vs 34.5%**
- Brier: **0.1348**
- log loss: **1.7010**

The bias appears at every position: QB upward 20.5% vs 31.9%, RB 21.0% vs 34.1%, WR 22.8% vs 37.6%, TE 21.8% vs 39.9%. Young players are especially affected: 30.5% upward predicted vs 47.3% realized, while downward is 43.1% vs only 21.0% realized.

This explains the earlier D2 defect. Historical transitions were learned from **realized-current production states**, but live D2 assigns state from **Forecast Y1 production**. Those state anchors are not exchangeable.

## D2 downstream result

Frozen D2 improved only trivially:

| Model | Realized-contribution MAE |
|---|---:|
| **A** | **23.26** |
| D2 before Forecast repair | 34.87 |
| D2 with repaired research transitions | **34.79** |

D2 still beat A in **0/12 chronological folds**. Developmental MAE worsened from 35.45 to **37.31** and young MAE from 53.60 to **55.12**. Elite, aging, WR and TE results improved somewhat, but not enough to offset the remaining state-anchor problem.

## Synthetic and current sanity

The D2 synthetic gates remain passed because D2 itself was not changed:

- stable starter QB **11.46** > weak-path high-variance backup **1.43**
- credible developmental QB **10.81**
- strong-upside WR **8.05** > weak-upside WR **1.44**
- elite TE **15.69** >> fringe TE **0.25**

Current live sanity used FFToday + Razzball. Bijan > Darnold and JSN > Judkins are coherent; QB ordering is sensible. But KC Concepcion still narrowly exceeds Brock Bowers, and Trey McBride remains above Bowers. More fundamentally, nearly every headline player still maps to `elite` from Forecast Y1, which mechanically leaves no upward transition and exaggerates decline probability from the top state.

Runtime remains trivial: about **0.048 seconds for 334 players**, or ~**2.6 ms** for an 18-player roster once reusable state tables are available.

## Architectural conclusion

The next defect is **not another Intrinsic problem** and not a reason to create D3.

Forecast needs a point-in-time **current-state anchor calibrated in the same Forecast/role coordinate used at inference**. The next research should reconstruct or learn that anchor from PIT forecast-like and/or role evidence, especially for RB/WR/TE, while retaining the existing governed QB meaningful-starter model. Then rerun the exact frozen D2 experiment.

TE-premium scoring propagation remains a separate upstream integration task.

**PR #138 remains unmerged pending explicit management approval.**
