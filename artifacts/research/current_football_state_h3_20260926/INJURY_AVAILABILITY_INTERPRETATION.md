# Dedicated Injury Availability / Time-to-Return Research Interpretation

Date: 2026-09-27  
Authority: **Research only / no production H3 or Intrinsic change**

## Executive conclusion

The dedicated injury phase supports exactly one additional component:

**A nonlinear remaining-season availability model clears the frozen chronological Research gates.**

The dedicated time-to-return challenger does **not** clear its frozen promotion threshold and remains unpromoted.

This is deliberately narrower than an "injury penalty."

Supported:
- probability/expected share of remaining current-season availability after a contemporaneous injury episode.

Not supported by this phase:
- a precise time-to-return model beyond coarse status/severity evidence;
- conditional healthy-production haircuts;
- post-return role multipliers;
- recurrence/reinjury penalties;
- generic H2/H3 injury effects;
- direct Intrinsic adjustments.

## Population and chronology

The study reuses the exact **4,793** already-governed historical injury episodes from 2012–2024.

No episode definition or severity label was reopened.

Scored chronological holdouts:
- 2019;
- 2020;
- 2021;
- 2022;
- 2023;
- 2024.

For every holdout, fitting and preprocessing used only earlier seasons.

Age and NFL experience were recovered from the already-governed career panel with **100% coverage** for these episodes.

Data hygiene:
- **185** old descriptive availability rows above 1.0 were bounded to the valid [0,1] availability target;
- **37** return-time rows whose old descriptive return delay exceeded the structural regular-season window were retained for bounded availability but excluded from the return-time target rather than inventing a return event.

## Remaining-season availability — accepted Research component

Frozen severity-only baseline, pooled OOT n=2,502:
- MAE **0.242579**
- RMSE **0.284977**
- bias **+0.009862**

Selected HistGradientBoosting challenger:
- MAE **0.223094**
- RMSE **0.275536**
- bias **-0.008206**

Relative MAE improvement: **8.03%**.

Frozen gate required >=2%.

Holdout MAE direction:
- improved in **6/6** seasons.

Position safety versus severity-only:
- QB: **10.67% MAE improvement**;
- RB: **7.82% improvement**;
- TE: **3.78% improvement**;
- WR: **9.68% improvement**.

No supported position violates the frozen 7% regression limit.

Result:
**remaining-season availability clears the Research evidence bar.**

This component estimates availability only. It must be multiplied/combined with a separately governed conditional-active production expectation only in a future authorized Forecast contract.

## Availability uncertainty

Chronological absolute-residual conformal bands were calibrated only from earlier seasons.

Across the final 2,502 OOT rows:
- nominal 80% band actual coverage: **85.01%**;
- nominal 90% band actual coverage: **93.84%**.

Position pooled coverage:
- QB: **83.74% / 92.12%**;
- RB: **87.25% / 95.56%**;
- TE: **83.77% / 92.70%**;
- WR: **84.39% / 93.59%**.

The accepted component therefore carries non-zero empirical uncertainty. No cross-target or cross-horizon covariance is claimed.

## Time to return — not promoted

Frozen severity-only baseline, pooled OOT n=2,486:
- mean endpoint Brier **0.113445**
- integrated Brier **0.094956**
- mean log loss **0.360485**
- mean absolute calibration error **0.017679**

Best challenger, HistGradientBoosting:
- mean endpoint Brier **0.111509**
- integrated Brier **0.091777**
- mean log loss **0.350499**
- mean absolute calibration error **0.014110**

Improvements:
- endpoint mean Brier: **1.71%**
- integrated Brier: **3.35%**
- endpoint Brier improves in **6/6** holdouts.

The frozen gate required >=2% mean-Brier improvement and >=1% integrated-Brier improvement.

The challenger therefore misses the primary materiality threshold by about **0.29 percentage points** and is **not promoted**.

Position safety itself was acceptable:
- QB Brier improves 2.71%;
- RB worsens 0.70%;
- TE improves 1.04%;
- WR improves 3.48%.

Research does not lower the frozen threshold after seeing the result.

Recommended behavior:
- preserve time-to-return as coarse direct status/severity evidence for now;
- retain the richer model as challenger evidence for future independent validation.

## Forecast contract implication

The evidence now supports a componentized non-production Research contract:

`H1 remaining expected points = remaining-season availability × conditional active production`

where:
- the availability component may use the accepted injury-availability model when an independently authorized fallback path is needed;
- conditional active production is **not** reduced merely because an injury exists;
- authoritative current ROS, if/when governed, owns the integrated H1 expectation and must not receive this model as a second haircut;
- post-return role, recurrence and H2/H3 durable effects remain separate unpromoted questions.

## Authority disposition

Production H3: unchanged.  
Production Intrinsic: unchanged.  
Provider ROS authority: unchanged.  
Direct injury penalty in Intrinsic: prohibited.  
Generic H2/H3 injury penalty: not supported.

The accepted result is **Research support for a dedicated remaining-season availability component only**.
