# Bounded New-Family Challenge — Symmetric Interpretation

Date: 2026-09-27  
Authority: **Research only / no production Forecast, H3 or Intrinsic change**

## Why this challenge was run

Before scoring N1/N2, the frozen breadth audit found that the serious recoverable whole-Forecast candidate set was concentrated in empirical / generalized-linear / Bayesian-ridge / hand-authored state-mixture families. It lacked both:
- a chronology-tested whole-Forecast nonlinear interaction learner; and
- a chronology-tested whole-Forecast smooth nonlinear / trajectory family

on the common multiyear Y2/Y3 production coordinate.

That pre-score finding triggered exactly two frozen challengers:
- **N1** — direct six-state HistGradientBoosting + state-conditioned HistGradientBoosting magnitude;
- **N2** — spline two-part persistence/state model + spline state-conditioned Ridge magnitude.

No tuning or additional family was added after outcomes were visible.

## Common evidence

Common rolling PIT coordinate:
- H2 origins 2014-2023: **5,726 rows**;
- H3 origins 2014-2022: **5,168 rows**;
- total: **10,894 rows**.

Comparators:
- **D0** — frozen active-magnitude representation;
- **D1** — frozen state-conditioned magnitude representation;
- N1;
- N2.

All four were scored on the same rows with the same target.

## Aggregate results

### H2

| Model | MAE | RMSE | State Brier | State log loss | CRPS |
| --- | ---: | ---: | ---: | ---: | ---: |
| D0 | 32.9871 | 50.4157 | 0.64536 | 1.35866 | 27.2129 |
| D1 | 32.1407 | 49.8747 | 0.64536 | 1.35866 | **21.9314** |
| N1 HistGB | 32.0059 | **49.5016** | 0.64824 | **1.36541** | **21.8650** |
| N2 spline | **31.7948** | 49.6428 | 0.64714 | 1.36946 | 22.4861 |

D1 vs N1:
- MAE difference is uncertain: N1 lower by 0.135, clustered CI crosses zero.
- CRPS is effectively tied: N1 lower by 0.066, CI crosses zero.
- state/probability differences are also uncertain.

D1 vs N2:
- N2 has lower point MAE centrally, but clustered MAE difference crosses zero.
- **D1 has materially lower CRPS** by 0.555, clustered 95% interval excluding zero.

N1 vs N2:
- point MAE difference is uncertain;
- **N1 has materially lower CRPS** by 0.621, clustered interval excluding zero.

H2 conclusion:
**D1 and N1 form the best-supported aggregate distributional set; N2 adds meaningful point-accuracy evidence but is not distributionally equivalent at the aggregate level.**

### H3

| Model | MAE | RMSE | State Brier | State log loss | CRPS |
| --- | ---: | ---: | ---: | ---: | ---: |
| D0 | 31.2273 | 50.0123 | 0.57936 | 1.23646 | 23.9412 |
| D1 | 30.9129 | 49.4086 | **0.57936** | **1.23646** | **19.8195** |
| N1 HistGB | **30.2538** | **49.1788** | 0.58809 | 1.26849 | 20.1527 |
| N2 spline | 30.5335 | 49.3583 | 0.58026 | 1.28164 | 20.4100 |

D1 vs N1:
- N1's lower MAE is directional but clustered interval crosses zero;
- **D1 has materially better state Brier and state log loss**;
- CRPS difference is uncertain.

D1 vs N2:
- point MAE difference is uncertain;
- state Brier is tied;
- **D1 has materially better state log loss and CRPS**.

N1 vs N2:
- point MAE / CRPS differences are uncertain;
- **N2 has materially better state Brier**.

H3 conclusion:
**D1 retains the strongest aggregate state/distribution evidence; N1 supplies a credible point-accuracy challenger. This is a tradeoff, not universal D1 authority.**

## Chronological robustness

Lowest-MAE counts by origin:
- H2: N2 5/10, N1 3/10, D1 2/10, D0 0/10.
- H3: N1 6/9, N2 3/9, D1 0/9, D0 0/9.

Lowest-CRPS counts:
- H2: N1 6/10, D1 4/10.
- H3: D1 6/9, N1 2/9, N2 1/9.

This is useful evidence that the point-vs-distribution tradeoff is not driven by a single season.

## D0 / D1 reinterpretation

D1 versus D0:
- H2 MAE improves by 0.846 with clustered CI excluding zero;
- H2 CRPS improves by 5.281 with clustered CI excluding zero;
- H3 CRPS improves by 4.122 with clustered CI excluding zero;
- H3 MAE improves 0.314 centrally, with interval crossing zero;
- state probabilities are identical by construction.

Symmetric conclusion:
**D1 is the better-supported magnitude representation than D0 on this common coordinate.**
This statement follows evidence, not incumbent status.

## Position-specific authority map

The cell map is persisted separately in `HORIZON_POSITION_AUTHORITY_MAP.csv`.

Key cells:
- H2 QB: D1 / N1 tradeoff-tie; N2 has materially weaker CRPS than D1.
- H2 RB: D1 / N1 / N2 practically tied; N1 has best central CRPS.
- H2 WR: **N2 has supported point-MAE advantage** over D1; distributional evidence remains tied.
- H2 TE: D1 / N1 tradeoff-tie; N2 has materially weaker CRPS.
- H3 QB: D1 / N1 tradeoff-tie; D1 materially outperforms N2 on CRPS.
- H3 RB: **N1 has supported point-MAE advantage** over D1 with no supported distributional loss.
- H3 WR: **N2 is best-supported**: supported point-MAE advantage over D1 and N1, distribution/state evidence tied with D1 and stronger than N1.
- H3 TE: D1 / N1 tradeoff-tie; N2 is weaker on point/distribution evidence.

## Breadth conclusion after the challenge

The audit's family-breadth requirement is now satisfied:
1. generalized-linear/state decomposition: present;
2. whole-Forecast nonlinear interaction learner: **N1 now tested**;
3. smooth nonlinear / trajectory family: **N2 now tested**;
4. persistence/survival representation: present through B1 / two-part persistence architectures;
5. coherent predictive distribution/state-mixture representation: present through D1 and the new families.

No additional model family is authorized by this audit. Opening more families now would be model shopping rather than resolution.

## Scientific disposition

There is **no universal Forecast family winner** on the common Y2/Y3 coordinate.

The evidence instead supports:
- D1 as the strongest general distributional benchmark;
- N1 as a serious nonlinear point-accuracy challenger, especially H3 / RB;
- N2 as a serious smooth nonlinear challenger, especially WR cells;
- cell-specific ties/tradeoffs rather than incumbent privilege.

Production Forecast / H3 / Intrinsic remain unchanged.
