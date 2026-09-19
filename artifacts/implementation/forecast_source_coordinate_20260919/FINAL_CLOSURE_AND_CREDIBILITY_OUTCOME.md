# FSFFL NEXT - Standard-vs-Half-PPR Closure & Controlled Credibility Gate

## Management outcome

**Source-coordinate closure: PASS — no scoring-unit implementation defect.**

The recovered 335-player preseason raw ensemble deterministically reproduces both required Year-1 coordinates:

- connected league 0.5-PPR board: `6bded35221a501471df60de8c05a6e691428552f23abb3f0cf799218fd71bfae`
- frozen I1 standard/non-PPR board: `dfe817909dc42782ef4f1249692a9ad9139b5fa25311549ae741970c4ef9efe9`
- population/identity parity: 335 / 335 on both coordinates.

P0/current-state assignment, I1 current/prior production features, and I1 target/state means all remain in the frozen standard/non-PPR coordinate. The current 2025 adapter is exact-parity validated to that research coordinate. The existing `LeagueScoringNormalizedI1Predictor` converts future I1 point quantities into connected-league units exactly once; it does not alter probabilities or I1 inputs.

Mechanical regression proof:
- repository CI: **1,228 passed**
- focused source-coordinate/Forecast/Intrinsic tests: **30 passed**

No source-coordinate code correction was required.

## Controlled current-player credibility gate

Mechanical path: **PASS**
- 335/335 identities and completed-source mappings
- frozen Year 1 from preserved preseason 0.5-PPR authority
- completed-source I1 inputs remain standard/non-PPR
- Y2/Y3 league scoring bridge exactly once
- targets 2026 / 2027 / 2028
- 2,048-permutation frozen Shapley
- no live-provider data used

Football credibility: **MODEL CONCERN — stop**

The gate exposes a material extreme-age persistence issue. Among QBs older than 36 in the controlled board, median Year-2 `out` probability is only **2.1%**:

| Player | Age | State | Y2 | Y3 | H2 out | H3 out |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Aaron Rodgers | 41.8 | elite | 199.1 | 185.9 | 0.005 | 0.017 |
| Joe Flacco | 40.6 | premium | 113.3 | 105.3 | 0.023 | 0.035 |
| Matthew Stafford | 37.6 | elite | 209.2 | 185.5 | 0.006 | 0.012 |
| Kirk Cousins | 37.0 | premium | 112.3 | 107.0 | 0.021 | 0.044 |
| Tyrod Taylor | 36.1 | starter | 39.5 | 47.7 | 0.085 | 0.060 |

The frozen feature contract groups every QB older than 31 into one `aging` category and caps the continuous experience feature at 15 years. The board therefore shows a credible structural concern that extreme career age is not being represented strongly enough in persistence risk.

This is **not** a standard-vs-half-PPR defect and is **not** repaired here. Correcting it would require a modeling/calibration decision, which is outside the authorized mechanical closure.

## One narrow follow-up question

**Does the frozen I1 age/experience representation materially understate persistence risk at extreme career ages, especially for QBs well beyond age 31, and if so what is the most defensible evidence-backed age representation/calibration that corrects this without named-player tuning or disturbing settled non-age architecture?**

## Boundary

No model fit, coefficient fit, named-player tuning, provider-weight change, fresh-provider substitution, merge, or deployment occurred.

**STOP FOR MANAGEMENT REVIEW.**
