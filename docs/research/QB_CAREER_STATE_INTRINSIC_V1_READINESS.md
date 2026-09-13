# QB Career-State + Intrinsic Value v1 — Production Readiness

Status: **READY FOR MANAGEMENT MERGE REVIEW**  
Production PR: #133  
Research PR: #131 remains research-only and unmerged.  
Base main validated: `f38e2f029a0d9563986635012336434a3f9beb63`  
QB integration validation head: `d0db2b3dcccb66fde3bd792cc42a6853569175c5`

## Purpose

This report is the durable release-readiness record for the Forecast-owned QB career-state model and its integration into FSFFL Intrinsic Value v1. It freezes the validated model contract, historical evidence, current-player shadow evidence, authority boundaries, versioning/provenance behavior, operational characteristics, limitations, and final release recommendation.

This is not a new research cycle. No coefficient, feature, threshold, player-specific rule, or Value economic parameter was tuned from the current-player shadow run.

## Frozen QB target and model contract

The target is:

**MEANINGFUL_STARTER = at least 200 pass attempts in the target NFL season.**

The production model is one pooled standardized maximum-likelihood logistic regression with a forecast-horizon indicator. Its frozen features are:

1. age;
2. NFL experience;
3. draft-pick percentile;
4. prior games participation;
5. prior passing-opportunity share;
6. two-year role mean;
7. two-year role volatility;
8. established-starter seasons;
9. current production percentile;
10. forecast horizon.

The model does **not** use an elite-QB training label, Market Value, dynasty rankings, QB-premium rules, team utility, contender state, named-player overrides, contract status, or a second conditional-production model.

Model version: `qb-career-state-logit-v1`  
Evidence version: `qb-career-state-evidence-v1`  
Current season-scoped evidence cutoff: 2025 for the 2026 artifact.

Conditional production after a meaningful-starting-role outcome remains deliberately conservative: Year-2 and Year-3 expected production equal the authoritative Year-1 Forecast mean multiplied by the corresponding meaningful-starter probability. There is no second survival adjustment.

## Point-in-time and chronology controls

Historical challenger evaluation was chronological. Features for each evaluation point were restricted to information available before the target outcome, and the production-shaped final comparison used chronological holdouts rather than random train/test splits.

The current 2026 deployment evidence artifact is season-scoped and contains prior-football evidence only. Runtime checks require the artifact evaluation season and feature cutoff to match the requested season. Stale, missing, ambiguous, or incomplete evidence fails closed instead of being silently reused.

The current compatibility identity bridge accepts only one exact normalized-name match when a canonical GSIS reference is unavailable. Canonical provider identity remains preferred.

## Historical QB forecast validation

The career-state challenger materially improved the frozen carry-forward baseline.

| Population | Metric | Carry-forward | Career-state | Improvement |
| --- | --- | ---: | ---: | ---: |
| All QB | Y2 MAE | 64.701 | **57.162** | **11.7%** |
| All QB | Y3 MAE | 74.221 | **62.019** | **16.4%** |
| All QB | cumulative MAE | 127.773 | **107.884** | **15.6%** |
| Elite QB | Y2 MAE | 90.788 | **83.331** | **8.2%** |
| Elite QB | Y3 MAE | 115.259 | **98.431** | **14.6%** |
| Elite QB | cumulative MAE | 187.841 | **158.933** | **15.4%** |

All-QB cumulative Spearman improved from **0.7086 to 0.7240**. Elite-QB cumulative Spearman improved from **0.3676 to 0.3751**.

The deployment-shaped 2017–2022 chronological comparison won **6/6 folds**. Fold-level integrated Intrinsic-v1 error improved in every target year:

| Target year | Prior Intrinsic v1 MAE | QB-integrated MAE | Improvement |
| --- | ---: | ---: | ---: |
| 2017 | 16.159 | **15.100** | 6.6% |
| 2018 | 22.174 | **21.800** | 1.7% |
| 2019 | 18.760 | **18.023** | 3.9% |
| 2020 | 19.301 | **17.183** | 11.0% |
| 2021 | 18.882 | **18.710** | 0.9% |
| 2022 | 18.681 | **17.799** | 4.7% |

There were **0 probability-bound violations or production explosions**, and the observed rate of Year-3 probability materially exceeding Year-2 probability was zero.

## Probability calibration

The model improves materially over the unconditional baseline and is well calibrated enough for the bounded production role it serves.

| Horizon | ROC-AUC | Brier | Baseline Brier | ECE |
| --- | ---: | ---: | ---: | ---: |
| Y2 | **0.910** | **0.1203** | 0.2410 | **0.0461** |
| Y3 | **0.875** | **0.1384** | 0.2285 | **0.0492** |

Elite-QB calibration also remains reasonable: Y2 mean predicted starter probability was about 0.856 versus 0.864 observed; Y3 was about 0.805 versus 0.782 observed.

## Effect on Intrinsic Value v1

The integrated historical reconstruction contains 9,430 out-of-time player/fold observations.

- affine control MAE: **26.968**;
- prior Intrinsic v1 MAE: **20.307**;
- QB-integrated Intrinsic v1 MAE: **19.981**;
- improvement versus affine: **25.9%**;
- incremental improvement versus prior Intrinsic v1: **1.6%**.

QB-only MAE improved from **56.932 to 54.350**, and QB Spearman improved from **0.521 to 0.565**. In the focused 2017–2022 QB subset, MAE improved from **59.610 to 52.255** and Spearman from **0.519 to 0.645**.

RB, WR, and TE outputs were numerically unchanged in the integration validation:

- RB MAE: 20.450 before and after;
- WR MAE: 14.825 before and after;
- TE MAE: 7.282 before and after.

That is an important safety result: the QB repair did not leak into non-QB Forecast or Value behavior.

## Current-player production-shape shadows

The live shadow workflow was frozen before inspection and required at least five representative successful cases plus bounded monotone probability trajectories. All six selected cases succeeded.

The run used two successful independent live Year-1 sources (`fftoday`, `razzball`) and produced 53 QB forecasts. CBS and NFL Fantasy were unavailable as usable full-season projection sources in that run; this was recorded rather than hidden.

| Role | Player | Y1 | P(Y2 starter) | P(Y3 starter) | Y2 expected | Y3 expected | Intrinsic before | Intrinsic after |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| elite established | Josh Allen | 375.06 | 0.945 | 0.922 | 354.54 | 345.93 | 305.52 | **448.61** |
| young highly drafted | Drake Maye | 323.30 | 0.927 | 0.897 | 299.75 | 290.12 | 173.53 | **311.21** |
| veteran established | Dak Prescott | 300.87 | 0.864 | 0.814 | 260.07 | 244.94 | 116.33 | **223.43** |
| fringe / competition | Daniel Jones | 269.85 | 0.627 | 0.536 | 169.29 | 144.73 | 37.23 | **45.10** |
| backup / uncertain | Malik Willis | 255.25 | 0.361 | 0.280 | 92.13 | 71.36 | 0.00 | **0.00** |
| rushing-heavy | Lamar Jackson | 318.20 | 0.915 | 0.881 | 291.18 | 280.34 | 160.52 | **291.98** |

All six moved from LOW deep-horizon confidence under the prior QB carry-forward treatment to MODERATE evidence confidence under the governed career-state path. Malik Willis remained at zero Intrinsic surplus in the test replacement context despite receiving nonzero starter probabilities, which is a useful indication that the model is not mechanically creating value for every QB.

These values are safety shadows, not named-player calibration targets.

## Authority boundaries

The production implementation preserves the FSFFL architecture:

- **Forecast owns QB career-state probability.** The model, feature resolution, evidence artifact, version checks, and current-player runtime are in `fsffl.forecast`.
- **Value consumes Forecast.** Value does not estimate QB survival or meaningful-starting-role probability itself.
- **Value owns replacement economics.** Intrinsic v1 uses marginal-lineup-opportunity replacement and weights 1.00 / 0.85 / 0.70.
- **Market remains separate.** Broad Market Value is not an input to Intrinsic v1.
- **League Market Value remains a separate coordinate.** It is not silently substituted for Intrinsic.
- **Team Utility remains downstream.** No team-specific utility or strategic posture signal enters the intrinsic coordinate.
- **Strategic posture and calculated competitive state remain separate concerns.** Neither is used to train or alter this QB model.

There is no duplicate QB career-state or survival calculation added in Value. Product routing invokes the Forecast-owned builder and passes its output into Value.

## Provenance, versioning, and fail-closed behavior

The in-process evidence artifact validates both its evidence version and model version before use. A version mismatch raises rather than continuing with an unknown contract.

The 2026 runtime also verifies evaluation season and row-level feature cutoff. A 2027 request cannot silently reuse the 2026 artifact; tests require that case to return no career-state estimate so Intrinsic falls back to conservative carry-forward.

The output records:

- model version;
- evidence version;
- evaluation season;
- feature cutoff season;
- current production percentile;
- Year-2 and Year-3 probabilities;
- Forecast policy version and provenance note in the Intrinsic path.

## Storage and performance

The deployment artifact is a small compressed, versioned in-process evidence payload built offline from historical football evidence. Runtime inference is a tiny standardized logistic calculation plus deterministic evidence lookup.

There is:

- no request-time historical scan;
- no request-time model fit;
- no required external historical service;
- no database migration;
- no Monte Carlo simulation added to this endpoint.

The current-player shadow workflow intentionally used live Year-1 Forecast providers as a safety test, but the QB career-state evidence itself is not fetched from an external service at request time.

## CI and reproducibility evidence

Historical integration workflow:
- run `34761412908`;
- artifact `qb-career-state-intrinsic-v1-validation`;
- artifact ID `10318986847`;
- result: **PASS**.

Current-player shadow workflow:
- run `34758807311`;
- artifact `qb-career-state-current-shadows`;
- artifact ID `10318023067`;
- result: **PASS**.

Full PR CI at integration head `d0db2b3dcccb66fde3bd792cc42a6853569175c5`:
- run `34761415721`;
- **1,160 tests passed**;
- two unrelated dependency deprecation warnings;
- no test failures.

The dedicated evidence artifacts are retained by GitHub Actions for 14 days; the durable numerical conclusions and contracts are preserved in this report.

## Known limitations

1. The current football-evidence artifact is explicitly season-scoped for 2026. A new season requires a new governed artifact/version rather than silent reuse.
2. Conditional production for a QB who remains a meaningful starter is intentionally the authoritative Year-1 mean. A second conditional-production model was not justified for v1.
3. Deep-horizon standard deviation is not newly refit by the QB challenger; the integration preserves authoritative Year-1 uncertainty rather than inventing an unvalidated variance rule.
4. The fallback identity bridge is intentionally strict. Ambiguous or missing identity evidence yields no career-state estimate.
5. Current live shadow evidence had two successful independent projection sources rather than all configured providers. This affected the safety-run evidence availability, not the frozen QB career-state model.
6. The model does not claim to solve League Market Value, owner behavior, trade acceptance, Team Utility, or all multi-year Forecast uncertainty.

None of these limitations requires a player-specific correction, market anchor, QB premium, or new Value model before v1 release.

## Final readiness recommendation

**MERGE PR #133 after final CI is green and management explicitly approves the merge.**

Rationale:

1. the QB challenger improves all-QB and elite-QB cumulative forecast error materially;
2. it wins all six chronological production-shaped QB holdouts;
3. probability calibration is strong and bounded;
4. integrated Intrinsic v1 improves overall and QB-specific out-of-time error while leaving RB/WR/TE unchanged;
5. current-player shadows are directionally coherent across elite, young, veteran, fringe, backup, and rushing-heavy archetypes;
6. Forecast/Value/Market/Team Utility authority boundaries remain intact;
7. provenance and version mismatches fail closed;
8. runtime cost is negligible and introduces no new external dependency;
9. no current-player hand tuning or unsupported QB premium was introduced.

This report does **not** authorize the merge by itself. PR #133 should remain unmerged until management gives explicit approval.
