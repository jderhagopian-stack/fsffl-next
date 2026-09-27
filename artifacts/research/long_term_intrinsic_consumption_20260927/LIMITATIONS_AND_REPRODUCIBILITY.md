# Long-Term Intrinsic — Limitations and Reproducibility

Date: 2026-09-27

## Exact execution

Research branch:
`research/long-term-intrinsic-consumption-20260927`

Starting durable Y4-Y8 authority head:
`2f58dde66c440e3dd29f5b86acb6906fa1fd6388`

Frozen consumer contract commit:
`562447d6bf5eb66eb3bfb3abc7c96b8a0e48a4f5`

Validation implementation commit:
`c690bd0b4337a5058e936163f19b631ee842ba84`

Workflow trigger commit:
`ce27d6ffc306734a0cfca62b8e36c2203a86240c`

Validation workflow:
- run `36352688339`;
- result: **success**;
- complete artifact `10943221137`;
- digest `sha256:d1c0132928631d7868549f2c9f27b9458f08ca062b86b83b8db448321bd3ef62`;
- retained through 2026-10-27.

Frozen reused rolling evidence:
- run `36271080037`;
- artifact `10916355135`;
- digest `sha256:63520ddb60a8ed12724fa21e8d276c4e3e7d5587162aade92ba7afaa3796ced2`.

Current shadow reused for downstream relationship only:
- run `36267757579`;
- artifact `10913539274`;
- digest `sha256:ee8abf0854b5d64f110413dca6699bce764bb7cbc48264d7becd588b7646c052`.

## Limitations

### 1. Only two complete Y4-Y7 outer origins

The strict four-year consumer requires realized Y4, Y5, Y6 and Y7 from the same PIT origin.

Only base seasons **2018 and 2019** satisfy that requirement in the already-governed rolling evidence, yielding 1,129 complete player-origin observations.

This is the binding validation limitation.

The result supports the economic consumer architecture and shadow implementation, but it is not strong enough by itself to claim final production-calibrated Long-Term Intrinsic accuracy across eras.

### 2. Not a pristine new final holdout

The Forecast policies were previously studied. This Research phase freezes the Value consumer before scoring it, but reuses known Forecast output rows.

Call the result a consumer validation / historical replay, not untouched Forecast confirmation.

### 3. Historical career-stage fields are not on the rolling policy output

Historical position validation is possible from the rolling rows; a clean career-stage split is not recoverable from that exact artifact without joining/reconstructing additional historical covariates.

The current 335-player shadow has age/experience bands and is used for descriptive archetype impact only.

No missing historical archetype split is fabricated.

### 4. Current 335-player long-term shadow is not the final set-valued contract

The available current shadow was produced by a prior frozen single long-horizon architecture.

It is sufficient to prove that a long-term lens would differ materially from Current Intrinsic.

It is **not** a substitute for future materialization of the exact current symmetric authority envelope.

### 5. Cross-horizon covariance remains unvalidated

Annual uncertainty can be propagated horizon by horizon and as conservative interval arithmetic.

No exact cumulative standard deviation, Gaussian lifetime band or independence-based variance sum is authorized.

### 6. Historical raw scale is zero-inflated

The full historical long-horizon panel includes many players who are no longer economically relevant four to seven years later; realized Long-Term raw has median zero.

That is appropriate for validation but unsuitable as a naive fixed linear 0-10,000 display ruler.

Use a separately versioned current-cohort rank-calibrated presentation index.

### 7. No revealed-market validation

Long-Term Intrinsic is market-independent by design. This study does not use future trade prices or current Market to tune the quantity.

Market and owner response remain downstream.

### 8. No team-specific window validation

The universal player quantity intentionally excludes contender/rebuilder timing preferences.

Team Utility must validate any future competitive-window weighting separately.

## Reproducibility outputs

Persisted compact outputs:
- `validation/LONG_TERM_HISTORICAL_METRICS.csv`;
- `validation/LONG_TERM_SHORTCUT_COMPARISON.csv`;
- `validation/LONG_TERM_AUTHORITY_ENVELOPE_VALIDATION.csv`;
- `validation/LONG_TERM_HISTORICAL_SCALE_KNOTS.csv`;
- `validation/CURRENT_VS_LONG_TERM_REFERENCE.csv`;
- `validation/CURRENT_LONG_TERM_ARCHETYPE_COMPARISON.csv`;
- `validation/LONG_TERM_INTRINSIC_VALIDATION_RESULT.json`.

The complete workflow artifact also retains the full annual historical Shapley replay.

## Authority guards

- Forecast family search: no;
- Forecast refit: no;
- Y8 cardinal inclusion: no;
- Market input: no;
- Team Utility input: no;
- production Current Intrinsic change: no.
