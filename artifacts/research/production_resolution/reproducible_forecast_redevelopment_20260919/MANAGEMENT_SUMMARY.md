# FSFFL NEXT - Reproducible Forecast Deployment Redevelopment

Date: 2026-09-19  
Authority: bounded research only  
Final outcome: **B - RESEARCH RESULT NOT READY FOR PROMOTION**

## Plain-English result

The redevelopment solved the reproducibility problem but failed the final credibility test.

The new D0/D1/D2 Forecast was fully specified before successful fitting, reconstructed the governed historical source coordinate, selected its routing only from historical evidence, survived the post-freeze replication check, and produced a final fitted package that replayed essentially exactly.

The one-time 335-player current board then exposed a different problem: **future production is still being compressed too aggressively for elite players even when the model expects them to remain active.**

That is exactly the kind of post-freeze credibility defect the directive said must stop promotion without tuning from current players.

## Historical selection

### Y2
Selected: **universal D1**.

- D0 MAE: 33.6510
- selected D1 MAE: 32.7880
- gain: 0.8630 points
- paired clustered 95% interval: [0.4325, 1.3068]
- D1 improved in early, mid, and validation chronological blocks.

### Y3
Selected: **position x broad career-stage D0/D1 routing**.

- D0 MAE: 31.8558
- selected route MAE: 31.3999
- gain: 0.4558 points
- paired clustered 95% interval: [0.1459, 0.7927]

Frozen Y3 route:
- QB developmental D0; QB established/veteran D1.
- RB developmental D1; RB established/veteran D0.
- WR developmental/established D1; WR veteran D0.
- TE developmental/established D1; TE veteran D0.

The already-inspected 2021-2022 years were used only after freeze as descriptive replication. They continued to improve versus D0: +0.8521 MAE points at Y2 and +0.3780 at Y3. They did not change the route.

## Exact deployment fit and replay

Final cutoff:
- Y2 source seasons through 2023, targets observable through 2025.
- Y3 source seasons through 2022, targets observable through 2025.

Final fitted package SHA-256:
`ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7`

Fresh-path replay:
- 20,610 rows.
- max probability difference: 4.996e-16.
- max point difference: 1.421e-13.
- route mismatches: 0.
- replay status: **PASS**.

So the final outcome is not a reproducibility failure.

## One-time 335-player current board

The board was materialized exactly once after replay passed.

- 335 governed players.
- 35 previously-null ages filled only from the already-governed exact-age completion.
- 300 mapped historical identities; 35 explicit unmatched/cold-start identities.
- current-player tuning actions after materialization: **0**.
- model/routing changes after materialization: **0**.

## The credibility defect

Among the **33 top-10% source producers**:

| Metric | Y2 | Y3 |
|---|---:|---:|
| Median active probability | 93.4% | 87.3% |
| Median conditional-active production / Y1 | 45.2% | 39.7% |
| Median unconditional expected points / Y1 | 41.3% | 34.1% |
| Share with conditional production below 60% of Y1 | 100% | 100% |

The problem is not limited to aging players.

Among the **14 age <=25 top-10% source producers**:

| Metric | Y2 | Y3 |
|---|---:|---:|
| Median active probability | 95.2% | 90.7% |
| Median conditional-active production / Y1 | 47.5% | 43.1% |
| Share below 60% conditional production / Y1 | 100% | 100% |

The top-10% conditional-production median is below 60% of Y1 at **QB, RB, WR, and TE** at both horizons.

## Required named examples

- **Bijan Robinson:** active probability 95.4% Y2 / 90.8% Y3, but conditional-active production is only 35.8% / 32.5% of Y1.
- **Jahmyr Gibbs:** 95.7% / 91.3% active, but 37.3% / 33.7% conditional production.
- **Puka Nacua:** 94.1% / 88.9% active, but 38.8% / 36.1% conditional production.
- **Christian McCaffrey:** 84.1% / 62.3% active, 37.0% / 30.6% conditional production.
- **Aaron Rodgers:** 67.3% / 37.5% active, 26.4% / 26.3% conditional production.
- **Sam Darnold:** 94.8% / 90.4% active, 52.7% / 50.5% conditional production.

Mechanically selected representative QBs were Carson Beck (developmental), Sam Darnold (established), and Jacoby Brissett (veteran).

## Directive question

**Is a healthy young elite player being compressed to a difficult-to-defend future production level even when the model expects him to remain active?**

**Yes.**

It is not an isolated named-player result. It is a systematic upper-tail pattern across positions. The model often assigns very high future active probabilities while simultaneously shrinking the player's production conditional on being active to roughly one-third to one-half of his governed Y1 level.

## Final decision

**OUTCOME B - RESEARCH RESULT NOT READY FOR PROMOTION.**

Historical selection passed. Reproducibility passed. Current-player credibility did not.

Per the directive:
- do not tune from these current players;
- do not automatically open another family;
- do not implement, promote, merge, or deploy;
- preserve the artifacts and **STOP FOR MANAGEMENT REVIEW**.
