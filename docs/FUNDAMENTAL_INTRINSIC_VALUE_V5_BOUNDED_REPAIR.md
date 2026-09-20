# Fundamental Intrinsic v5 — bounded shared-scale repair

This document records the focused merge-blocking correction applied on PR #138 after current-player validation exposed two defects in v4. It does not reopen the Fundamental Intrinsic architecture.

## Preserved architecture

Fundamental Intrinsic remains team-independent long-term dynasty asset worth derived from football fundamentals. Canonical State and governed Forecast remain authoritative. Broad Market, future League Market, replacement surplus, Team Utility, owner behavior, roster need, and transaction prices remain outside Intrinsic. The validated residual-draft-pedigree methodology is preserved.

## Defect 1 — continuation was too position-wide

v4 approximated all post-Year-3 value as:

`0.85^3 × Y3 mean × position coefficient`

The same coefficient applied to a position regardless of age. This materially overstated remaining-career value for aging non-QBs, most visibly Derrick Henry and Dallas Goedert.

Two broader refits were tested and rejected because they degraded chronological validation. The promoted repair is narrower: preserve the validated parent continuation coefficient for QB and for young/prime non-QBs, and use historically fitted position × age-band continuation factors only for veteran/late non-QBs.

Non-QB age bands are: young <=23, prime 24–26, veteran 27–29, late 30+.

Promoted continuation factors:

| Position / state | Factor |
|---|---:|
| QB parent | 4.081433 |
| RB parent | 4.751363 |
| RB veteran | 4.288215 |
| RB late | 2.520767 |
| WR parent | 5.255558 |
| WR veteran | 6.266997 |
| WR late | 1.782412 |
| TE parent | 4.229937 |
| TE veteran | 3.383854 |
| TE late | 3.708186 |

These are empirical state-conditioned continuation cells, not arbitrary youth bonuses. A cell may be above or below its parent when historical football evidence supports it; the strong late-career collapses are concentrated where the data supports them.

## Defect 2 — final raw coordinate was position-relative

v4 computed shared discounted football career production, then divided it by a different 90th-percentile career anchor for QB/RB/WR/TE. That made `100` mean roughly “premium for this position,” not one common dynasty-worth magnitude.

v5 removes that final positional normalization. The production raw coordinate is now:

`Raw Fundamental Intrinsic = discounted Y1–Y3 football production + state-conditioned post-Y3 continuation + residual pedigree in shared football units`

The old position anchors remain only as unit-conversion constants for the already-validated pedigree residual coefficient. They no longer normalize or rank the final coordinate.

## Chronological validation

The selected repair was evaluated on the same 8,196 point-in-time examples and nine chronological holdout folds used by the existing calibration workflow.

| Diagnostic | v4 | v5 repair |
|---|---:|---:|
| Shared-unit MAE | 128.0686 | 126.3157 |
| Fold wins | — | 9 / 9 |
| Top-decile MAE | 355.9578 | 352.5715 |
| QB MAE | 304.4659 | 304.4659 |
| RB MAE | 110.5212 | 108.0023 |
| WR MAE | 112.3663 | 110.7398 |
| TE MAE | 77.3459 | 75.4393 |

Age-30+ diagnostics also improve: RB MAE 82.3365 → 69.9750; WR 120.2417 → 103.0111; TE 68.1691 → 66.8832.

The two rejected broader candidates worsened aggregate shared-unit MAE by about 4.1% and lost almost every chronological fold. They were not promoted.

## Current-player sanity gate

| Player | Position | v4 raw | v5 shared raw | v4 display | v5 display |
|---|---:|---:|---:|---:|---:|
| Josh Allen | QB | 182.3 | 1909.6 | 9793 | 9798 |
| Lamar Jackson | QB | 144.6 | 1514.9 | 9646 | 9645 |
| Drake Maye | QB | 160.3 | 1678.8 | 9717 | 9719 |
| Bijan Robinson | RB | 328.2 | 1352.8 | 9974 | 9553 |
| CeeDee Lamb | WR | 174.0 | 821.0 | 9768 | 9044 |
| Brock Bowers | TE | 271.9 | 793.0 | 9943 | 9005 |
| Kyle Pitts | TE | 182.8 | 533.0 | 9795 | 8511 |
| Derrick Henry | RB | 184.1 | 618.4 | 9799 | 8741 |
| Quinshon Judkins | RB | 192.5 | 793.2 | 9821 | 9005 |
| Jonathon Brooks | RB | 156.5 | 645.0 | 9701 | 8806 |
| KC Concepcion | WR | 125.9 | 553.9 | 9538 | 8567 |
| Tyler Allgeier | RB | 74.9 | 308.7 | 8339 | 7250 |
| Dallas Goedert | TE | 119.6 | 333.3 | 9484 | 7443 |
| Rhamondre Stevenson | RB | 118.5 | 468.8 | 9466 | 8259 |
| Troy Franklin | WR | 38.1 | 167.5 | 5613 | 5366 |
| Drew Lock | QB | 1.3 | 13.6 | 513 | 1131 |
| Devin Duvernay | WR | 2.4 | 11.0 | 954 | 1022 |

The named pathologies are resolved. Derrick Henry no longer outranks Josh Allen; Kyle Pitts no longer outranks Josh Allen; Jonathon Brooks no longer outranks Lamar Jackson. Henry post-Y3 continuation falls from about 299.2 to 158.8. Goedert post-Y3 continuation falls from about 124.6 to 109.2 and, more importantly, the common raw coordinate places him far below apex QBs rather than normalizing him toward their tier.

## Display v5

The v4 display transform used percentiles from the full football population and compressed ordinary rosterable assets toward 10,000. v5 uses fixed/versioned raw shared-magnitude anchors derived only from the repaired historical football distribution.

The stable reference universe is the historical half of repaired predictions at or above the pooled median shared raw magnitude (`107.3390`). This rule uses no position quota, league roster rule, market price, or named-player tuning. Fixed football-only reference quantiles then establish a monotonic presentation curve, with 9,000 reserved for the reference universe's extreme p99 magnitude (`789.6240`) and an asymptotic tail above it.

This creates semantic comparability with Broad Market without fitting to it: the numeric regions communicate the same broad dynasty-asset magnitude language—fringe, depth, meaningful, premium, apex—while each coordinate remains independently derived. A disagreement such as Broad Market 6,800 versus Intrinsic 8,200 is therefore meaningful rather than engineered away.

## Independence proof

The selected calibration target is shared-unit six-season discounted realized football production. Calibration metadata explicitly records `market_inputs_used=false`, `replacement_inputs_used=false`, `team_utility_inputs_used=false`, and `owner_inputs_used=false`. Production Intrinsic consumes governed Forecast, canonical PlayerState age/pedigree evidence, and frozen football-only coefficients. No market provider or transaction price is a feature, anchor, fitting target, loss function, or display anchor.
