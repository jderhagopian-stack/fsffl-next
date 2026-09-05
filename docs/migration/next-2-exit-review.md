# NEXT-2 Forecast Engine — Exit Review

Status: **PASS**

NEXT-2 is ready to merge once the CI run on this exit-review commit is green.

This review closes the Forecast authority layer. It does not promote research-only challenger weights, create dynasty value, or move downstream decision logic into Forecast.

## Exit gates

### Real modern historical ingest — PASS

The `NEXT-2 Historical Benchmark` workflow acquires retained research inputs at runtime rather than committing third-party projection datasets to this public repository. The 2024 and 2025 projection objects, realized season outcomes, and player-ID crosswalk are normalized into a provider/player historical panel.

Latest completed benchmark evidence used for this review: workflow run `33958374013` on commit `91d93128e22f67134221f741c93e925a2e4f4910`.

The workflow completed successfully after schema and identity hardening. The extracted panel contained 6,646 matched provider/player observations: 3,328 for 2024 and 3,318 for 2025.

### Real multi-source comparison — PASS

The retained panel contains independent underlying provider rows and does not give the carrier repository an additional forecast vote. Provider results are reported by position with sample sizes and coverage so differing observed cohorts are not mistaken for apples-to-apples superiority.

### Chronological held-out evaluation — PASS

The empirical study uses:

- training: 2024;
- held-out test: 2025.

No 2025 realized outcome is used to choose challenger weights. Forecast/outcome matching requires exact player, position, metric, and target period identity.

### Baseline versus challenger — PASS

Equal weighting remains the baseline. A challenger learned only from 2024 is applied to the common-source/common-player 2025 held-out cohort.

On 438 paired held-out players:

- equal-weight MAE: 44.60;
- challenger MAE: 44.43;
- challenger-minus-equal MAE: -0.18, paired bootstrap interval [-0.32, -0.03];
- equal-weight RMSE: 62.13;
- challenger RMSE: 61.97;
- challenger-minus-equal RMSE: -0.16, paired bootstrap interval [-0.30, -0.01].

The improvement is real but small and comes from one chronological split. **The challenger is not promoted to permanent production authority.** More seasons are required to establish year-to-year stability and to compare all-history, rolling, decayed, and shrunk approaches empirically.

### Uncertainty treatment — PASS

Forecast distributions carry uncertainty explicitly. Ensemble uncertainty combines source uncertainty and inter-source disagreement. Historical calibration diagnostics can evaluate standardized error and interval coverage. The held-out benchmark uses paired bootstrap uncertainty for model comparisons.

Career transitions now propagate observed development/decline dispersion mathematically rather than applying an arbitrary long-horizon uncertainty multiplier. Quantiles are not naively rescaled through a zero-inflated career-survival mixture.

### Provider portability / source governance — PASS

Provider-specific acquisition and field mapping remain at the adapter edge. Core Forecast contracts do not depend on provider payload schemas.

Source governance separates predictive role from access/rights status. Aggregators are not automatically treated as independent raw-stat votes. Research acquisition at workflow runtime does not imply redistribution or production-commercial rights. Provider-specific production promotion still requires appropriate provenance and rights review.

### Aging / development — PASS

NEXT-2 does not copy legacy aging curves.

The career-transition calibration path can select historical cohorts by:

- position;
- horizon;
- age range;
- experience range;
- career stage;
- rookie status;
- prior production;
- prior usage;
- research-defined production/usage bands.

The core does not hard-code universal age, usage, or production thresholds. Those cohort definitions belong to a versioned calibration study. Point-in-time evidence cutoffs prevent future seasons from entering historical estimates. Narrow cohorts fail closed when the study's explicit minimum support is not met, allowing deliberate pooling/shrinkage rather than silent guessing.

Rookies can be modeled separately from veterans. Weak cohorts expose sample size and standard errors instead of pretending to have veteran-level certainty.

### Multi-year football treatment — PASS

Multi-year forecasts roll forward explicit career-transition evidence. Each step separates:

- conditional football production/development;
- survival/attrition probability;
- transition dispersion;
- base forecast uncertainty.

No fallback career coefficient is hidden in runtime code. Multi-year Forecast remains a football-outcome distribution and contains no market price, dynasty value, roster-fit, contender, or trade logic.

### Downstream provider independence — PASS

Downstream consumers receive canonical forecast contracts. They need not know which provider supplied source projections and must not recreate provider-specific projection logic.

### CI — PASS subject to final commit check

CI was green on the completed implementation immediately before this review (`1b1ff65ef12bf4db3913d89cba66388088d0395a`, run `33958639124`). The review itself is documentation-only; its own CI run must also complete successfully before merge.

## Explicit non-blocking follow-on research

The following work improves Forecast over time but is not required to keep NEXT-2 open:

- extend chronological projection benchmarking deeper toward 2019–2025;
- add useful independent providers when rights and point-in-time provenance permit;
- compare all-history, rolling-window, exponential-decay, and hierarchical/shrunk weighting across multiple held-out seasons;
- build richer historical career-transition calibration datasets and research cohort definitions;
- improve stat-level forecast primitives and derive league-specific fantasy points through canonical LeagueRules;
- add richer injury, role, usage, and rookie-development evidence as it becomes supportable.

These are Forecast research/calibration improvements, not reasons to delay the Value layer once the authority contract is sound.

## Boundary check

NEXT-2 answers: **What is likely to happen on the football field?**

It does not answer:

- what a player is worth in dynasty;
- what the market will pay;
- what a player is worth to a specific roster;
- how much a transaction changes championship odds;
- whether a trade should be accepted.

Those remain downstream responsibilities of NEXT-3 through NEXT-6.

## Exit decision

**PASS.** Once CI is green on this review commit, merge PR #3 and begin NEXT-3 Value immediately.
