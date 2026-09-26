# FSFFL NEXT — Current Comparative Y4+ Diagnostics

Date: 2026-09-26  
Authority: Research shadow only.

## Primary versus rejected routed sensitivity

Historical selection was frozen before these current-player shadows.

Primary annual Y4-Y8 family:
**two_part_state across all positions/horizons.**

Rejected routed curve remains sensitivity-only.

| H | Primary vs routed rank Spearman | Median abs rank diff | P90 | Max | Top25 overlap | Top50 overlap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 0.999486 | 1 | 2.6 | 25 | 25 | 50 |
| 5 | 0.998787 | 1 | 4.0 | 35 | 25 | 49 |
| 6 | 0.996677 | 2 | 8.6 | 52 | 24 | 48 |
| 7 | 0.995397 | 3 | 10.6 | 61 | 24 | 49 |
| 8 | 0.994726 | 3 | 11.0 | 63 | 24 | 49 |

The average current ranking is robust, while the long-horizon tail contains meaningful model risk.

Largest mechanically selected sensitivity examples include young QBs such as Jalon Daniels, Ty Simpson, Cade Klubnik and Will Howard. These rows were inspected only after historical model selection was frozen and are not tuning targets.

## Primary horizon movement

| H | H3 vs H rank Spearman | Median abs move | P90 | Max | ≥10 ranks | ≥20 ranks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 0.993854 | 4 | 12 | 95 | 15.5% | 3.0% |
| 5 | 0.985711 | 7 | 19 | 123 | 36.1% | 9.3% |
| 6 | 0.976823 | 10 | 23 | 147 | 52.5% | 17.9% |
| 7 | 0.970965 | 11 | 27 | 165 | 55.8% | 23.3% |
| 8 | 0.967170 | 12 | 30 | 173 | 59.4% | 25.4% |

The movement curve is gradual. There is no current-player discontinuity that rescues a Y5 breakpoint.

## Position composition

Top-25:
- H3: QB 88%, RB 8%, WR 4%, TE 0%.
- H4: QB 80%, RB 8%, WR 12%, TE 0%.
- H5: QB 76%, RB 8%, WR 16%, TE 0%.
- H6: QB 76%, RB 12%, WR 12%, TE 0%.
- H7: QB 76%, RB 12%, WR 12%, TE 0%.
- H8: QB 72%, RB 12%, WR 16%, TE 0%.

Top-50:
- H3: 52% QB / 32% RB / 16% WR / 0% TE.
- H5: 50% / 26% / 24% / 0%.
- H8: 50% / 20% / 30% / 0%.

Top-100:
- H3: 31% QB / 31% RB / 32% WR / 6% TE.
- H5: 29% / 29% / 35% / 7%.
- H8: 29% / 28% / 35% / 8%.

## Current-player examples under the retained family

Examples are diagnostic only:
- J.J. McCarthy: H3 rank 269 → H4 174 → H5 146 → H6 122 → H7 104 → H8 96.
- Justin Fields: 281 → 215 → 174 → 158 → 149 → 145.
- Troy Franklin: 231 → 179 → 155 → 133 → 128 → 119.
- Elic Ayomanor: 248 → 206 → 172 → 156 → 142 → 139.
- Keenan Allen: 204 → 221 → 226 → 228 → 233 → 236.
- Brian Robinson: 182 → 197 → 207 → 209 → 214 → 214.

These illustrate time-profile differences; they are not evidence for manual youth/age coefficients.

## Precision by position

Holdout `two_part_state` annual rank signal at Y4 → Y8:
- QB Spearman: 0.615 → 0.579 → 0.563 → 0.490 → 0.477.
- RB: 0.465 → 0.395 → 0.351 → 0.254 → 0.203.
- WR: 0.557 → 0.507 → 0.486 → 0.440 → 0.410.
- TE: 0.515 → 0.420 → 0.383 → 0.335 → 0.212.

Survival calibration remains useful, but exact annual point precision becomes weak relative to expected magnitude, particularly RB and TE.

Research interpretation: no model-family breakpoint is supported, but product precision must still degrade visibly with horizon.
