# Forecast Stable Player-Level Correction — Production-Readiness Review

**Status:** production-readiness audit only; research-only/shadow; no authoritative Forecast change; no production PR; PR #131 remains research provenance and must not be merged by this review.

## Executive conclusion

**Recommendation: DO NOT PROMOTE the current research formulation.**

The stable player-level residual signal is real and materially useful for future production-level accuracy. On the subset of historical paths where the research correction is actually eligible, it improves Year-2, Year-3, and cumulative error and is chronologically robust. Elite-QB level accuracy improves materially and the principal young-WR, young-TE, and aging-RB safety checks remain within predeclared tolerances.

However, the current research formulation is not production-safe as authoritative mean behavior. Its empirically estimated deeper-horizon translation can generate pathological individual corrections: the observed Year-2 adjustment tail reaches about **+256 fantasy points**, including an example based on only two prior resolved residual seasons despite empirical-Bayes shrinkage. The formula has no explicit production-safe bound, and the user-facing production contract for this review requires the correction to be bounded. Adding a cap, stronger shrinkage, recency rule, or position-specific multiplier after seeing this failure would be a new nearby residual formula and is explicitly outside this review.

A second operational limitation remains: production persists point-in-time provider projection revisions, but that store explicitly preserves source/provider evidence rather than authoritative FSFFL ensemble Forecast truth. The research correction requires historical residuals against the point-in-time authoritative Forecast. A trustworthy current-player shadow therefore cannot be produced from the existing governed production history without adding or reconstructing a new authoritative Forecast-history contract.

The signal should remain research provenance. This review does not reopen persistence research, does not propose another correction family, and does not begin Model A production work.

## Current repository state inspected

- Exact current `main`: `f38e2f029a0d9563986635012336434a3f9beb63`.
- PR #131 before this report: `26aca439deed9f20e6e68c432a6d7d61fe0ee74b`, open, draft, unmerged, research-only.
- PR #132 remains roadmap/docs-only and non-overlapping.
- Current production Forecast does **not** already contain a materially equivalent player-specific residual correction.

The authoritative multi-year Forecast in `src/fsffl/forecast/career.py` applies cohort transition evidence to the incoming Forecast distribution. No resolved player-specific historical residual term is added to the mean.

## What the correction is

For a completed season, the research residual is:

`realized production - the point-in-time Forecast for that season`.

Only residuals whose outcomes were already resolved at the forecast cutoff are eligible. The research implementation requires at least two prior residual seasons before any personal signal can activate.

For an eligible player it estimates the player's multi-season average residual and applies empirical-Bayes shrinkage toward a point-in-time cohort prior. The personal component is the shrunken player estimate **minus the cohort prior**, so the mechanism is intended to correct persistent individual bias rather than count a general cohort effect twice.

The cohort fallback hierarchy is:

1. position × career stage × production tier;
2. position × career stage;
3. position;
4. global.

Year 1 is unchanged. For Years 2 and 3, the research candidate applies a chronologically estimated horizon translation coefficient to that shrunken personal residual component. Translation evidence itself is restricted to previously resolved historical applications and has a minimum evidence floor.

This is a **level correction**. It is not momentum, hot-hand logic, a revision-persistence multiplier, a market premium, an age bonus, a QB premium, or an elite-player override.

## Predeclared production gates

Before the new readiness stress output was inspected, the following material thresholds were declared:

- at least **1.5% relative MAE improvement** in Year 2, Year 3, and cumulative eligible forecasts;
- cumulative improvement in at least **60%** of eligible chronological folds;
- no chronological fold more than **5% worse**;
- key subgroup cumulative/per-horizon degradation no worse than **2%**, with elite-QB safety tightened to **1%**;
- exact zero personal correction with fewer than two resolved residuals;
- no pathological correction tail;
- safe behavior when residual direction reverses or player residuals are highly volatile;
- Year 1, survival, and Forecast uncertainty remain unchanged;
- no market input or downstream duplicate correction;
- a governed point-in-time residual source must be available for operational production use;
- the correction must remain interpretable and production-bounded.

## Historical accuracy — eligible paths

The headline PR #131 all-path result was:

| Metric | Current research baseline | Player-residual candidate |
|---|---:|---:|
| Year-2 MAE | 36.979 | 36.014 |
| Year-3 MAE | 35.557 | 34.773 |
| Cumulative MAE | 67.398 | 66.066 |

For production-readiness, the more relevant comparison is the **3,722 common paths where the player-specific correction is actually eligible**:

| Metric | Baseline | Candidate | Relative improvement |
|---|---:|---:|---:|
| Year-2 MAE | **37.585** | **35.958** | **4.33%** |
| Year-3 MAE | **36.040** | **34.684** | **3.76%** |
| Cumulative MAE | **71.872** | **68.633** | **4.51%** |

All three clear the predeclared 1.5% accuracy threshold.

## Chronological stability

There are 15 evaluable historical forecast folds. The first two produce no correction while sufficient prior translation evidence accumulates. Cumulative error improves in **12 of 15 folds (80%)** and is unchanged in the first two. No cumulative fold is materially worse; the tiny Year-2 degradation in 2009 is approximately 0.01% while cumulative error still improves slightly.

Later folds show increasingly consistent gains, with cumulative relative improvement reaching roughly 3.7%–6.8% in the 2014–2021 range.

This clears the chronological robustness gates and is evidence that the aggregate signal is not driven by one holdout period.

## Subgroup safety

On eligible paths:

| Subgroup | n | Year-2 change | Year-3 change | Cumulative change | Gate |
|---|---:|---:|---:|---:|---|
| Elite QB | 152 | **+6.79%** | **+6.95%** | **+11.59%** | PASS |
| Young breakout WR | 176 | **+0.52%** | **+1.84%** | **+2.08%** | PASS |
| Young TE | 237 | **+0.27%** | **+0.16%** | **+1.08%** | PASS |
| Aging RB | 409 | **-0.70%** | **-0.11%** | **-0.72%** | PASS within 2% tolerance |

The candidate therefore preserves the useful elite-QB production-level finding and does not create a material average subgroup regression under the declared thresholds.

## Sparse-history and cold-start behavior

The research implementation correctly gives **zero player-specific correction with 0 or 1 prior resolved residual season**. Rookies and other cold-start players therefore receive no fabricated personal signal.

Among eligible Year-2 cases:

- exactly 2 prior residuals: `n=1,099`, MAE **43.668 -> 43.097** (**1.31% improvement**);
- exactly 3: `n=808`, **45.378 -> 44.831** (**1.20% improvement**);
- 4: `n=588`, **42.537 -> 41.123** (**3.33% improvement**);
- 5: `n=422`, **42.486 -> 40.992** (**3.51% improvement**);
- longer histories generally show larger average gains.

Thus the shrinkage mechanism behaves sensibly **on average**. But sparse-history safety is not fully established at the individual tail: the single largest observed positive adjustment came from a player with only **two** prior residual seasons. That is a material production-safety failure even though the two-season group improves in aggregate.

## Outlier robustness — failed gate

This is the decisive failure.

For eligible Year-2 adjustments, absolute correction magnitudes have approximately:

- median: **0.96 points**;
- 90th percentile: **20.86**;
- 95th percentile: **32.22**;
- 99th percentile: **68.53**;
- 99.5th percentile: **87.35**;
- maximum: **255.79 points**.

The maximum adjustment is about **3.55×** its baseline forecast magnitude.

Representative extreme historical shadow cases include:

- QB path: baseline **97.85 -> 353.64**, a **+255.79** adjustment, from only two prior residuals;
- another QB path: **167.06 -> 319.79**, **+152.72**;
- RB path: **85.29 -> 0.00**, a **-85.29** adjustment;
- QB path: **248.39 -> 380.40**, **+132.02**.

These tail corrections are not merely noise in aggregate: the high-adjustment tail can improve historical MAE on average. But the production question is stricter than whether the tail happened to help historically. An authoritative mean mechanism must be bounded and defensible for an individual live player. The present research formula has no production-safe bound on the translated personal residual and therefore fails the predeclared outlier/interpretability safety gate.

No cap or alternative shrinkage rule is introduced in this review because doing so after observing the holdout tail would be a new correction formula.

## Residual reversals, volatility, and staleness

When the latest residual reverses sign relative to the player's longer-run residual mean, the candidate still improves Year-2 MAE on average:

- no sign reversal: `n=2,666`, **50.022 -> 47.482** (**5.08% improvement**);
- reversal: `n=1,056`, **36.810 -> 36.186** (**1.70% improvement**).

Residual-volatility quartiles also all improve on average, from about **2.3%** in the lowest-volatility quartile to roughly **4.5%** in the highest.

However, the research player mean has no explicit recency decay. Older resolved residuals remain part of the personal mean until diluted by new evidence and shrinkage. Aggregate reversal performance is reassuring, but it does not establish a production contract for major role/team/position discontinuities or guarantee that stale player bias cannot remain influential after a genuine structural change.

No recency bonus, role-change override, or special-case decay is added here.

## Team, missed-season, role, and position-change handling

The research signal is attached to stable player identity and uses resolved historical production residuals. It does not itself contain a governed causal rule for:

- team changes;
- a return from a missed season;
- a major role discontinuity;
- a historical position-designation change.

These conditions are partly reflected in subsequent realized residual evidence, but the current formula does not explicitly distinguish persistent player skill/bias from a structural context break. The aggregate chronology is favorable, yet this remains another reason not to treat the current formula as fully production-governed without changing the research definition.

## Year 1, trajectory, uncertainty, and survival

The research correction leaves Year 1 unchanged by design. It alters only the deeper production **level**. Forecast uncertainty and survival are not changed by this mechanism.

The earlier research found that cumulative production levels improve while player-specific revision persistence remains weakly identifiable. This review preserves that distinction. No new persistence rule is introduced, and the correction is not allowed to become a hidden multiplier on how strongly new information carries through the path.

## Current/live shadow feasibility

A trustworthy current-player shadow was **not produced**.

Production has a durable append-only PostgreSQL store for source/provider projection revisions. That adapter explicitly states that it does not score, ensemble, impute, or create Forecast truth; callers request provider evidence, while the immutable preseason baseline is handled separately. The stable player-level correction, however, requires historical residuals against the authoritative point-in-time FSFFL Forecast, not merely historical provider projections.

No existing production contract inspected in this review supplied the required multi-season authoritative Forecast-vintage residual history in a form that can be joined directly to resolved outcomes for live correction. Creating current examples by substituting provider history, reconstructing vintages ad hoc, or using today’s Forecast retrospectively would violate the point-in-time contract.

Therefore the absence of current-player examples is itself an operational readiness finding rather than missing presentation work.

## Downstream integration implications

If this correction were ever promoted, it would belong only in Forecast. The changed mean would naturally propagate to consumers of authoritative Forecast output, including multi-year player trajectories, future Intrinsic Value, and any Simulation/Decision/Search path that consumes those Forecast means.

A production implementation would require at least:

- an explicit Forecast model-version/fingerprint change;
- invalidation of cached artifacts derived from the old Forecast means;
- a governed authoritative Forecast-history/resolved-outcome input contract for computing residual state;
- provenance sufficient to explain player history count, cohort fallback, shrinkage/reliability, and applied correction;
- confirmation that downstream schemas continue to consume the same `ForecastDistribution` shape without independent reapplication of the correction.

No API schema change is inherently required because the correction changes an existing mean rather than introducing a new required output field. No downstream module should recreate the residual adjustment independently.

No such production integration was implemented because the acceptance gates failed.

## Acceptance-gate results

| Gate | Result | Finding |
|---|---|---|
| Overall Year-2 accuracy | **PASS** | Eligible MAE improves 4.33%. |
| Overall Year-3 accuracy | **PASS** | Eligible MAE improves 3.76%. |
| Cumulative accuracy | **PASS** | Eligible MAE improves 4.51%. |
| Chronological robustness | **PASS** | 12/15 folds improve cumulatively; first two are zero while evidence accumulates. |
| Elite-QB safety | **PASS** | Cumulative MAE improves 11.59%. |
| Aging-RB safety | **PASS** | 0.72% cumulative degradation, within 2% tolerance. |
| Young-WR safety | **PASS** | No material degradation; cumulative improves 2.08%. |
| Young-TE safety | **PASS** | No material degradation; cumulative improves 1.08%. |
| Sparse-history cold start | **PASS / TAIL CONCERN** | 0–1 history receives zero correction; 2-history group improves on average, but contains the largest individual adjustment. |
| Outlier robustness / boundedness | **FAIL** | Individual correction tail reaches +255.79 points; no production-safe bound exists. |
| Recency / reversal | **PARTIAL** | Reversal cases improve on average, but no explicit staleness/decay contract exists. |
| Role/team/position discontinuity | **NEEDS GOVERNANCE** | No explicit structural-break handling in current research definition. |
| Market independence | **PASS** | No Market Value or dynasty price input enters the correction. |
| No double counting | **PASS in research design** | Personal component subtracts cohort prior; no downstream production implementation exists to duplicate it. |
| Year-1 invariance | **PASS** | Year 1 unchanged. |
| Survival/uncertainty invariance | **PASS** | This correction does not modify either. |
| Operational PIT history | **FAIL for promotion** | Provider history exists, but authoritative multi-season FSFFL Forecast residual history is not available under the inspected live production contract. |
| Interpretability | **PARTIAL / FAIL at tail** | Core EB logic is interpretable, but extreme translated corrections are not production-safe. |
| Operational performance | **NOT THE BLOCKER** | Arithmetic is cheap; history/provenance and invalidation are the substantive operational work. |

## Production PR decision

**No clean production PR was created.**

The current formulation fails the predeclared boundedness/outlier gate and does not have the necessary governed live authoritative Forecast-history input for safe deployment. Under the stopping rule, this review does not test nearby caps, stronger shrinkage, recency weights, position multipliers, elite overrides, or another residual family.

## Evidence provenance

The production-readiness calculations reuse the governed PR #131 point-in-time research artifact from workflow run `34724290153`, artifact `10307760543`, `pr131-model-a-intrinsic-forecast-audit`, SHA-256 `3748c331105a163fc3a2ba9b4fc8439811e623a27e4258b06368eeba31f2779c`. The corresponding research workflow previously completed with **1,153 tests passed, 2 warnings**.

This review adds no production code and therefore has no candidate production workflow or candidate production artifact.

## Management recommendation

**DO NOT PROMOTE the current stable player-level correction formulation.**

This is not a finding that player-specific historical residuals are useless. The opposite is true: the point-in-time evidence shows a credible, chronologically robust production-level signal. The reason for non-promotion is that the exact research mechanism is not yet a safe production contract: its individual correction tail is unbounded enough to violate the predeclared safety requirement, and current production does not expose the authoritative historical Forecast-residual state needed for honest live application.

Per the stopping rule, do not reopen player-specific persistence research, do not invent another residual formula in this review, and do not begin Model A production-readiness work until management reviews this result.