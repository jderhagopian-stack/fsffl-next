# Joint Injury-Availability Follow-up Gates

Date: 2026-09-27  
State: **FROZEN BEFORE JOINT SCORING**

These gates test whether one coherent shared architecture improves return timing **without sacrificing** the already-supported remaining-season availability result.

## Minimum support

Joint scoring must include:
- at least 1,500 outer-holdout episodes overall;
- all six outer holdout seasons 2019-2024;
- position safety where a position has at least 100 scored episodes.

Failure of minimum support rejects the joint challenger.

## A. Remaining-availability preservation gate

The joint architecture's Stage-A availability output must first continue to clear the original severity-only gate:
- >=2% relative pooled MAE improvement vs severity-only;
- pooled RMSE not >3% worse than severity-only;
- absolute pooled bias not worse by >0.02;
- MAE improves vs severity-only in at least 4/6 holdouts;
- no supported position >7% worse than severity-only.

It must also be non-inferior to the already-supported separate HistGradientBoosting benchmark:
- pooled MAE no more than **1% worse**;
- pooled RMSE no more than **1% worse**;
- absolute bias no more than **0.01** participation-share worse;
- no supported position MAE more than **3% worse**;
- no more than two holdout seasons may have MAE >3% worse.

Because Stage A intentionally freezes the accepted separate architecture, any material mismatch must be treated as an implementation/reproducibility failure, not rationalized after scoring.

## B. Return-timing promotion gate

The joint return head must clear the original return-timing evidence bar vs severity-only:
- >=2% relative improvement in pooled mean endpoint Brier;
- >=1% relative improvement in pooled integrated Brier;
- pooled probability log loss not >3% worse;
- mean absolute calibration error not worse by >0.02;
- no supported position mean Brier >7% worse;
- mean endpoint Brier improves in at least 4/6 holdouts.

It must also show direct improvement over the already-scored separate HistGradientBoosting return challenger:
- pooled mean endpoint Brier must be **strictly lower**;
- pooled integrated Brier may not be >1% worse;
- no supported position mean Brier may be >3% worse;
- joint mean endpoint Brier must be no worse than the separate challenger in at least 3/6 holdouts.

A joint architecture that merely reproduces the rejected separate return score does not advance the evidence.

## C. Calibration / uncertainty

For remaining availability:
- recompute the same chronology-preserving absolute-residual conformal 80% and 90% bands;
- report pooled and position coverage;
- no zero uncertainty.

For return timing:
- report pooled endpoint Brier, integrated Brier, log loss, calibration error, holdout stability, and position safety;
- do not claim a pristine untouched final-holdout uncertainty guarantee.

## D. Follow-up interpretation rule

This is comparative follow-up evidence on already-observed outer years. Therefore:
- passing supports a stronger **Research** architecture only;
- failing retains the existing separate availability component and rejected precise return-time model;
- neither outcome authorizes a production H3, Intrinsic, provider-authority, or direct injury-penalty change.

## E. Terminal state

After scoring and durable persistence:
- if all joint gates clear: `MANAGEMENT GATE — RESEARCH` with the joint architecture as the Research challenger;
- otherwise: `DIRECTIVE COMPLETE — RESEARCH` for this follow-up study, explicitly retaining the prior separate-model disposition.

In both cases, preserve Y4-Y8 long-horizon work as the next Research priority under OPERATING_PROTOCOL.md.
