# FSFFL Intrinsic Value v1 — Production Decision

Status: **PRODUCTION CANDIDATE — READY FOR MANAGEMENT MERGE REVIEW**  
Production PR: #133  
Base main validated: `f38e2f029a0d9563986635012336434a3f9beb63`

## Decision

Promote FSFFL Intrinsic Value v1 after final green CI and explicit management approval. The production candidate combines authoritative current-season Forecast, the frozen position/horizon deep-Forecast policy, the validated Forecast-owned QB career-state model, and transparent Model A replacement-adjusted economics.

The candidate remains market-independent, versioned, bounded, and explicit about evidence strength. No Model B, market anchor, named-player override, QB premium, or Team Utility change is included.

## Frozen Forecast-input policy

| Position | Year 1 | Year 2 | Year 3 |
| --- | --- | --- | --- |
| QB | authoritative current | QB career-state probability × Y1 conditional production when governed evidence is valid; otherwise carry fallback | same |
| RB | authoritative current | bounded career transition when governed evidence is available | bounded career transition when governed evidence is available |
| WR | authoritative current | conservative carry-forward | bounded career transition when governed evidence is available |
| TE | authoritative current | bounded career transition when governed evidence is available | bounded career transition when governed evidence is available |

Missing, stale, ambiguous, or incomplete deep-horizon evidence fails closed to conservative carry-forward. The same contract applies to every player.

## QB career-state contract

The QB target is a meaningful starting role, defined as **at least 200 pass attempts in the target NFL season**.

The production model is a single pooled standardized maximum-likelihood logistic regression with a horizon indicator and these features: age, NFL experience, draft-pick percentile, prior games participation, prior passing-opportunity share, two-year role mean, two-year role volatility, established-starter seasons, current production percentile, and forecast horizon.

It does not use an elite label, market/dynasty value, QB-premium rule, named-player override, contract feature, or a second conditional-production model. Conditional starter production remains the authoritative Year-1 mean.

Versions:
- QB model: `qb-career-state-logit-v1`;
- QB evidence: `qb-career-state-evidence-v1`;
- Forecast policy: `intrinsic-v1-forecast-policy-2`;
- Intrinsic model: `intrinsic-value-v1`;
- replacement context: `marginal-lineup-opportunity-v1`;
- raw scale: `fsffl_intrinsic_surplus` version `1`.

## Historical validation

The career-state challenger improves the QB carry-forward baseline materially:

- all-QB cumulative MAE: **127.773 → 107.884** (~15.6% better);
- all-QB Y2 MAE: **64.701 → 57.162** (~11.7% better);
- all-QB Y3 MAE: **74.221 → 62.019** (~16.4% better);
- elite-QB cumulative MAE: **187.841 → 158.933** (~15.4% better);
- all-QB cumulative Spearman: **0.7086 → 0.7240**;
- deployment-shaped chronological folds: **6/6 wins**;
- probability/trajectory bound violations: **0**.

Calibration is strong: Y2 Brier **0.1203** versus 0.2410 baseline with ROC-AUC **0.910** and ECE **0.046**; Y3 Brier **0.1384** versus 0.2285 with ROC-AUC **0.875** and ECE **0.049**.

## Effect on Intrinsic Value v1

On 9,430 out-of-time player/fold observations:

- affine control MAE: **26.968**;
- prior Intrinsic v1 MAE: **20.307**;
- QB-integrated Intrinsic v1 MAE: **19.981**;
- improvement versus affine: **25.9%**;
- incremental improvement versus prior Intrinsic v1: **1.6%**.

QB MAE improves from **56.932 to 54.350** and QB Spearman from **0.521 to 0.565**. RB, WR, and TE outputs are numerically unchanged by the QB integration.

The prior disclosed elite-QB carry-forward weakness is therefore **superseded by the validated QB career-state integration**. Elite-QB forecasting is still not perfect, but it is no longer evidence for retaining generic QB carry-forward as the v1 production policy.

## Model A economics

For each horizon:

`surplus_y = max(0, player Forecast_y - marginal-lineup-opportunity replacement Forecast_y)`

Then:

`raw intrinsic = 1.00 × surplus_Y1 + 0.85 × surplus_Y2 + 0.70 × surplus_Y3`

The raw coordinate is weighted expected fantasy-point surplus above replacement. Replacement is determined from actual league lineup structure: fixed position starters, then FLEX, then SUPERFLEX. Value does not apply QB survival again because Forecast already incorporates meaningful-starter probability in the expected QB mean.

## Current-player safety shadows

A frozen live shadow workflow tested Josh Allen, Drake Maye, Dak Prescott, Daniel Jones, Malik Willis, and Lamar Jackson. All six produced valid governed career-state paths; all satisfied `0 <= P(Y3) <= P(Y2) <= 1`; no named-player tuning followed inspection.

Representative P(Y2)/P(Y3):

- Josh Allen: **0.945 / 0.922**;
- Drake Maye: **0.927 / 0.897**;
- Dak Prescott: **0.864 / 0.814**;
- Daniel Jones: **0.627 / 0.536**;
- Malik Willis: **0.361 / 0.280**;
- Lamar Jackson: **0.915 / 0.881**.

The backup/uncertain example remained at zero Intrinsic surplus in the test replacement context, showing that nonzero role probability does not mechanically create franchise value.

Full current-player values, provenance, historical metrics, calibration, artifact IDs, limitations, and readiness evidence are preserved in `docs/research/QB_CAREER_STATE_INTRINSIC_V1_READINESS.md`.

## Confidence / completeness

- **HIGH** — authoritative current-season Forecast.
- **MODERATE** — governed bounded career transition or governed QB career-state evidence.
- **LOW** — conservative carry-forward/fallback.

QB deep horizons now receive MODERATE evidence when a valid career-state artifact row is available. Missing/stale evidence falls back to LOW carry-forward rather than fabricating a probability.

## Authority boundaries

The candidate preserves the governed architecture:

- Forecast owns QB career-state inference and evidence provenance;
- Value consumes Forecast and owns replacement economics;
- Broad Market Value does not enter Intrinsic;
- League Market Value remains a separate nullable coordinate;
- Team Utility remains downstream;
- strategic posture remains separate from calculated competitive state;
- no duplicate survival/career-state calculation exists in Value.

## Operational behavior

The QB evidence is a compact, season-scoped, versioned artifact built offline from prior football data. Runtime inference is a deterministic logistic calculation and lookup. There is no request-time historical scan, model fit, external historical provider dependency, database migration, or simulation.

Artifact/model version mismatches raise; stale seasons, missing age, unknown identity, and ambiguous identity fail closed. The 2026 artifact cannot silently serve a 2027 request.

## Validation evidence

- QB historical integration: workflow run `34761412908`, artifact `10318986847`, **PASS**.
- Current-player shadows: workflow run `34758807311`, artifact `10318023067`, **PASS**.
- Full CI at QB integration head `d0db2b3dcccb66fde3bd792cc42a6853569175c5`: run `34761415721`, **1,160 passed**, 2 unrelated dependency deprecation warnings.

## Known limitations

The evidence artifact must be regenerated/versioned for future seasons; conditional starter production remains the conservative Year-1 mean; the QB challenger does not create a new deep-horizon variance model; strict identity resolution can reduce coverage; and this work does not claim to solve League Market Value, owner behavior, trade acceptance, or Team Utility.

Those limitations are explicit and do not justify a market anchor, manual QB premium, player override, or new Value family for v1.

## Production recommendation

**MERGE PR #133 once final CI is green and management explicitly approves the merge.**

The QB career-state addition materially improves QB and elite-QB trajectory accuracy, improves integrated Intrinsic v1, leaves non-QB outputs unchanged, passes current-player safety shadows, remains lightweight operationally, and preserves all authority boundaries.

PR #133 must remain unmerged until management gives explicit approval.
