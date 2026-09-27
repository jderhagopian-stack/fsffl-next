# Injury Joint vs Separate — Symmetric Authority Reinterpretation

Date: 2026-09-27  
Authority: **Research only / no production change**

The old follow-up correctly applied its frozen study gate, but that gate included a direct replacement-margin condition. Under the newly authorized symmetric authority rule, that margin is historical provenance, not scientific privilege.

## Remaining-season availability

The separate HistGB and joint architecture are an **exact numerical tie**:
- MAE: 0.2230936664 for both;
- RMSE: 0.2755360405 for both;
- expected active weeks: 4.069119956 for both;
- active-weeks MAE: 1.373958459 for both;
- every pairwise difference and interval is exactly zero.

Both materially improve over severity-only:
- availability MAE gain 0.01949, clustered 95% interval [0.01086, 0.02837] for joint vs severity;
- active-weeks MAE gain 0.08199 weeks, interval [0.02890, 0.13625].

Scientific conclusion:
**joint and separate architectures have equal authority for remaining-season availability because they produce the same availability output.**

## Return timing

Pooled exact OOT rows, n=2,486:

| Model | Endpoint Brier | Integrated Brier | Log loss | Calibration error |
| --- | ---: | ---: | ---: | ---: |
| Severity | 0.113141 | 0.094956 | 0.359362 | 0.017679 |
| Separate HistGB | 0.110935 | **0.091777** | **0.348305** | **0.014110** |
| Joint | **0.110759** | 0.092949 | 0.353819 | 0.030047 |

Joint vs separate clustered differences:
- endpoint Brier: joint better centrally by 0.000176; CI **[-0.005897, +0.005893]**;
- integrated Brier: separate better centrally by 0.001171; CI **[-0.006735, +0.003701]** when expressed as joint gain;
- log loss: separate better centrally by 0.005514; CI **[-0.032252, +0.014866]**;
- calibration: separate better centrally by 0.01594; CI **[-0.031251, +0.005091]** when expressed as joint gain.

Every clustered pairwise interval includes zero.

Chronology is mixed:
- joint beats separate on only 2/6 outer seasons for endpoint Brier;
- 2/6 for integrated Brier;
- 2/6 for log loss.

Position evidence is also mixed:
- joint endpoint Brier is better for RB/WR;
- separate endpoint Brier is better for QB/TE;
- integrated/log-loss directions vary by position.

## Symmetric disposition

**TRADEOFF / NO SINGLE PRECISE RETURN-TIME AUTHORITY.**

The old statement “joint fails the direct-comparison gate” remains true as a description of that frozen experiment. It no longer means “the separate model is scientifically superior.”

The symmetric evidence says:
- remaining-season availability: exact tie;
- precise return timing: neither joint nor separate has a supported pairwise advantage;
- status/severity remains a coarse comparator, not a reason to manufacture a learned precision claim.

Production H3, Intrinsic, healthy-production treatment, provider ROS authority and no-double-counting remain unchanged.
