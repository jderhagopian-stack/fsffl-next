# Routed Forecast — candidate by position / career-state scorecard

Date: 2026-09-18  
Coordinate: `routed_forecast_aligned_candidate_coordinate_compact_v1.csv`  
SHA-256: `8095788e1b48028c50b65d7fba51ac48a41daceeaa6459ae3a219723ce30b1eb`

Career-state definition was frozen before this scorecard:
- developmental: experience 0–3
- established: experience 4–8
- veteran: experience 9+

Numbers below are MAE gains versus B2a: positive means the candidate has lower MAE. R1/R2 must replicate on early/mid/validation with at least 20 rows in every required fold. H2 has no legal early evaluation and therefore uses mid/validation only with the same support floor.

| Pos | Career state | H | N early/mid/val | R1 gain e/m/v | R2 gain e/m/v | H2 gain m/v | Frozen |
|---|---|---:|---:|---:|---:|---:|---|
| QB | developmental_0_3 | Y2 | 47/35/44 | -8.64/-6.20/-10.69 | -7.93/-6.07/-10.64 | -5.36/-8.93 | B2a |
| QB | developmental_0_3 | Y3 | 45/33/43 | -1.69/-10.64/-15.27 | -1.23/-10.49/-15.26 | -8.43/-13.09 | B2a |
| QB | established_4_8 | Y2 | 43/30/34 | +5.20/+0.19/+10.77 | +6.84/+0.48/+12.09 | +2.59/+12.85 | R2 |
| QB | established_4_8 | Y3 | 33/29/29 | +4.97/+0.84/+4.04 | +5.57/+1.62/+4.65 | +1.16/+5.83 | R2 |
| QB | veteran_9_plus | Y2 | 40/23/21 | +20.69/+24.69/+15.13 | +22.50/+27.24/+15.41 | +28.59/+15.40 | R2 |
| QB | veteran_9_plus | Y3 | 34/18/14 | +17.25/+29.20/+4.08 | +17.82/+30.38/+4.70 | +30.97/+4.84 | B2a |
| RB | developmental_0_3 | Y2 | 202/141/163 | -3.32/+1.68/-1.71 | -3.21/+1.60/-1.59 | +2.01/-0.86 | B2a |
| RB | developmental_0_3 | Y3 | 157/127/130 | -4.14/-1.39/-4.71 | -4.02/-1.35/-4.66 | -0.96/-3.22 | B2a |
| RB | established_4_8 | Y2 | 70/40/48 | +1.67/-4.30/-2.86 | +1.18/-4.35/-2.54 | -3.64/-1.70 | B2a |
| RB | established_4_8 | Y3 | 39/29/33 | +0.24/+1.39/-4.95 | -0.02/+1.27/-4.73 | +0.79/-4.49 | B2a |
| RB | veteran_9_plus | Y2 | 8/7/3 | +8.51/+0.21/-13.82 | +8.67/-0.18/-13.27 | +0.16/-10.18 | B2a |
| RB | veteran_9_plus | Y3 | 7/3/0 | +10.62/+5.60/— | +10.50/+6.50/— | +7.25/— | B2a |
| TE | developmental_0_3 | Y2 | 139/95/100 | -0.62/-0.02/-0.93 | -0.68/+0.12/-0.87 | +0.42/-0.16 | B2a |
| TE | developmental_0_3 | Y3 | 120/84/84 | -0.77/-0.26/-0.02 | -0.79/-0.26/+0.02 | -0.09/+0.29 | B2a |
| TE | established_4_8 | Y2 | 58/45/47 | +0.08/+1.71/-1.17 | +0.40/+1.91/-0.72 | +1.92/-0.43 | B2a |
| TE | established_4_8 | Y3 | 39/35/30 | +0.29/-0.55/-3.27 | +0.66/-0.31/-3.03 | +0.10/-1.75 | B2a |
| TE | veteran_9_plus | Y2 | 14/9/5 | +2.25/-2.14/+1.80 | +1.92/-2.46/+1.58 | -2.34/+3.23 | B2a |
| TE | veteran_9_plus | Y3 | 13/5/3 | -0.02/-2.18/-8.62 | -0.25/-2.39/-8.67 | +0.86/-7.46 | B2a |
| WR | developmental_0_3 | Y2 | 234/169/189 | +1.16/+1.00/-0.94 | +1.14/+1.00/-1.01 | +1.60/-0.63 | B2a |
| WR | developmental_0_3 | Y3 | 202/142/152 | +1.19/-2.57/-1.55 | +1.24/-2.56/-1.57 | -1.60/-0.85 | B2a |
| WR | established_4_8 | Y2 | 103/60/78 | +0.37/-3.65/-6.41 | +0.56/-3.82/-5.92 | -3.41/-4.91 | B2a |
| WR | established_4_8 | Y3 | 72/49/60 | +0.02/-1.26/-2.97 | -0.37/-1.35/-2.37 | -1.02/-1.51 | B2a |
| WR | veteran_9_plus | Y2 | 10/11/11 | -3.16/-10.58/+3.33 | -3.72/-10.34/+3.49 | -9.61/+4.23 | B2a |
| WR | veteran_9_plus | Y3 | 5/8/5 | -4.90/-6.89/-15.69 | -4.95/-6.66/-15.88 | -5.35/-10.91 | B2a |

## Route-selection result

Only three cells satisfy the frozen support/replication rule:
- QB established, Y2
- QB established, Y3
- QB veteran, Y2

R2 is selected in all three. R2 improves on R1 across those selected cells and the combined paired uncertainty for R1 -> R2 is positive:
- QB established Y2: +1.162 MAE; 95% paired interval [+0.497, +1.820]
- QB established Y3: +0.660; [+0.199, +1.133]
- QB veteran Y2: +1.632; [+0.851, +2.448]

H2 does not displace R2. On its mid/validation-only coordinate, the R2 -> H2 difference is not stably separated from zero for any frozen cell; H2 also carries the documented missing-early limitation.

QB veteran Y3 shows directionally favorable errors but fails the predeclared support floor (18 mid, 14 validation) and therefore defaults to B2a.

All RB/WR/TE cells and developmental QB cells default to B2a because their candidate gains are mixed, negative, or sparse.
