# Injury Shock Decomposition — Interpretation

Date: 2026-09-27  
Authority: **Research interpretation only**

The historical study contains **4,793 injury episodes**. These episode summaries are descriptive conditional cohorts. They are not causal estimates and must not be converted directly into player-value penalties.

## Remaining-season availability

Severity clearly stratifies remaining-season participation:

| contemporaneous severity | n | mean remaining participation share | median games to return |
| --- | ---: | ---: | ---: |
| limited/questionable | 2,701 | 0.802 | 0 |
| doubtful/out | 1,655 | 0.427 | 2 |
| reserve/IR/PUP/NFI | 437 | 0.281 | 1 |

This supports **separating remaining-season availability from player quality**.

It does **not** validate a universal injury multiplier. The broad availability/participation Forecast layer failed the predeclared OOT promotion gate at H1, H2 and H3.

## Conditional healthy production

Median post-return fantasy-points-per-active-game ratios were:
- limited/questionable: **0.879**;
- doubtful/out: **0.877**;
- reserve/IR/PUP/NFI: **0.852**.

These ratios are not causal injury effects. They combine injury severity, role changes, age, player quality, team context and regression. The OOT event-rich model did not show enough incremental calibration benefit to justify turning them into a healthy-production haircut.

Recommended behavior: **do not reduce conditional healthy production merely because an injury flag exists.**

## Post-return role / opportunity

Median post-return opportunity ratios:
- limited/questionable: **0.955**;
- doubtful/out: **0.980**;
- reserve/IR/PUP/NFI: **0.837**.

Non-reserve cohorts are near prior opportunity on the median; reserve cases show a larger descriptive role decline. This justifies keeping **post-return role/opportunity as a separate Forecast component**, but not a fixed multiplier.

A future role updater must beat current role/production baselines chronologically before promotion.

## Recurrence / reinjury

Observed recurrence-after-return shares:
- limited/questionable: **0.496**;
- doubtful/out: **0.280**;
- reserve/IR/PUP/NFI: **0.259**.

The recurrence definition captures repeated injury-limited episodes/reporting after return; it is not a biological reinjury probability. No recurrence coefficient is promoted from this result.

## Durable H2/H3 effect

Descriptive Y2/Y3 positive-production persistence remains high across all three severity classes:
- limited/questionable: **0.971 / 0.949**;
- doubtful/out: **0.947 / 0.923**;
- reserve/IR/PUP/NFI: **0.955 / 0.930**.

These high persistence rates are selection-conditioned and are not evidence that injuries have no durable effect.

The stronger result is the OOT model comparison:
- any-injury, non-IR injury and reserve-injury event layers fail the frozen H1/H2/H3 gate;
- no injury cohort produces >=2% qualifying improvement without violating another gate requirement.

Therefore **no generic injury-driven H2/H3 adjustment is supported**.

## Position / injury-family differences

The episode artifact includes position and broad injury-family breakdowns, and those cohorts show material descriptive heterogeneity. The current study does not establish age/experience-specific causal injury penalties or a position-specific durable multiplier.

Any future injury model should predict separate outcomes:
1. remaining-season active-game availability / time to return;
2. conditional healthy production;
3. post-return opportunity;
4. recurrence state;
5. H2/H3 survival/role.

Those targets should be validated separately under chronology.
