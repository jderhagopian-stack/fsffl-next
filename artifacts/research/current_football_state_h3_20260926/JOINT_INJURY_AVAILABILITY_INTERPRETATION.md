# Joint Injury-Availability Follow-up Interpretation

Date: 2026-09-27  
Authority: **Research only / no production H3 or Intrinsic change**  
Validation label: **follow-up comparative validation, not a pristine untouched final holdout**

## Executive conclusion

The frozen joint `availability_latent_hazard` architecture does **not** clear all predeclared follow-up gates.

It materially improves the headline return-timing Brier score and preserves the accepted remaining-season availability result exactly, but its integrated return-time Brier is **1.28% worse than the already-scored separate HistGradientBoosting return challenger**, exceeding the frozen 1% direct-comparison non-inferiority limit.

Therefore the joint architecture is **not promoted**.

Research disposition remains:
- keep the supported separate HistGradientBoosting remaining-season availability component;
- keep precise learned time-to-return **unpromoted**;
- retain coarse direct status/severity evidence for return timing;
- archive the joint system as challenger evidence only.

No gate was relaxed after scoring.

## Frozen evidence and chronology

The study reused the same governed **4,793 injury episodes** from 2012-2024.

Outer follow-up holdouts:
- 2019;
- 2020;
- 2021;
- 2022;
- 2023;
- 2024.

The Stage-B return head consumed only chronology-preserving inner Stage-A latent scores. For the 2019 outer origin, for example, the return head used inner origins 2016-2018; later outer origins added only earlier seasons.

The exact separate-model benchmark artifact from workflow run `36323231951` / artifact `10933510516` was restored directly. No friendlier benchmark was recomputed after the joint result was observed.

## Remaining-season availability — preserved exactly

The joint Stage-A availability output intentionally froze the already-supported HistGradientBoosting architecture.

Pooled OOT n=2,502:

| Model | MAE | RMSE | Bias |
| --- | ---: | ---: | ---: |
| Severity baseline | 0.242579 | 0.284977 | +0.009862 |
| Separate HistGB | 0.223094 | 0.275536 | -0.008206 |
| Joint Stage A | 0.223094 | 0.275536 | -0.008206 |

Maximum absolute prediction difference between the joint Stage-A output and the exact separate HistGB benchmark:
**1.11e-16**.

Thus:
- original availability gate: **PASS**;
- direct non-inferiority to the separate accepted model: **PASS**;
- holdout MAE improves versus severity in **6/6** seasons;
- no holdout is >3% worse than the separate model;
- all supported positions reproduce the separate-model MAE to numerical precision.

Chronological conformal coverage is therefore unchanged from the accepted separate model:
- nominal 80% band: **85.01% actual pooled coverage**;
- nominal 90% band: **93.84% actual pooled coverage**.

## Return timing — improved headline score, but joint direct-comparison gate fails

Pooled OOT n=2,486:

| Model | Mean endpoint Brier | Integrated Brier | Log loss | Mean abs calibration error |
| --- | ---: | ---: | ---: | ---: |
| Severity baseline | 0.113445 | 0.094956 | 0.360485 | 0.017679 |
| Separate HistGB challenger | 0.111509 | 0.091777 | 0.350499 | 0.014110 |
| Joint system | 0.110238 | 0.092949 | 0.354030 | 0.030047 |

Versus severity, the joint system:
- improves mean endpoint Brier by **2.83%**;
- improves integrated Brier by **2.11%**;
- improves endpoint Brier in **5/6** holdouts;
- stays within the original log-loss, calibration and position-safety limits.

So the joint system **does clear the original return-timing gate** that the separate HistGB challenger had narrowly missed.

Versus the exact separate HistGB return challenger, the joint system:
- improves pooled mean endpoint Brier by **1.14%**;
- is no worse on mean endpoint Brier in **4/6** holdouts;
- stays within the frozen 3% position non-inferiority limit, with TE the weakest cell at **2.77% worse**;
- but worsens integrated Brier by **1.28%**.

The frozen direct-comparison gate allowed at most a **1%** integrated-Brier regression.

That single direct-comparison condition fails. All other direct-comparison conditions pass.

## Interpretation

The shared availability latent contains useful information for whether a player has returned by the named 1/2/3/4-week endpoints and by season end. However, the joint head slightly worsens the shape of the full return-time probability path between those endpoints relative to the separate HistGB challenger.

That is exactly the tradeoff the frozen integrated-Brier guard was designed to catch.

The evidence therefore does **not** justify replacing the separate architecture with the joint system.

## Authority disposition

Supported Research component:
- separate HistGradientBoosting **remaining-season availability** model.

Not promoted:
- joint injury-availability architecture;
- precise learned time-to-return model;
- conditional healthy-production adjustment;
- post-return role adjustment;
- recurrence/reinjury penalty;
- durable H2/H3 injury penalty.

Unchanged:
- production H3;
- Intrinsic;
- current provider ROS authority;
- no-double-counting rule.

## Study terminal state

**DIRECTIVE COMPLETE — RESEARCH**

This terminal state applies to the joint injury-availability follow-up only.

The next Research priority is the preserved **Y4-Y8 long-horizon track**, resuming from its existing durable cell-specific Management gate without restarting completed evidence.
