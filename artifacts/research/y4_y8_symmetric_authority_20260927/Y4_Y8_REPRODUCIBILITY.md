# Y4-Y8 Symmetric Authority — Reproducibility and Durable Closeout

Date: 2026-09-27

## Durable branch

`research/y4-y8-symmetric-authority-20260927`

Exact interpretation starting head supplied by Management:
`cf35f1c540fb50507c41d95314509ea9081573f6`

That commit is:
`Research: persist Y4-Y8 symmetric authority evidence`

No model fitting, candidate search, or completed symmetric workflow was rerun after that durable head. Finalization consists only of interpretation and derived summaries from already-persisted evidence.

## Symmetric audit execution

Workflow:
- run: `36339388953`;
- conclusion: **success**;
- trigger head: `1d2ad8c8c409512ce92a4c9965ec0afcb3bb76a2`.

Workflow artifact:
- id: `10938860177`;
- name: `y4-y8-symmetric-authority`;
- digest: `sha256:d2c9e3a87f74c7f94fd4c6c932f3f5cda806165629f2ed22ec7d3bc9943c68af`;
- retained through 2026-10-27.

Persisted symmetric evidence:
- `PROTOCOL.md`;
- `Y4_Y8_SYMMETRIC_POLICY_SUMMARY.csv`;
- `Y4_Y8_PAIRWISE_UNCERTAINTY.csv`;
- `Y4_Y8_ORIGIN_DIRECTION.csv`;
- `Y4_Y8_CELL_AUTHORITY_MAP.csv`;
- `Y4_Y8_AGE_EXPOSURE_METRICS.csv`;
- `Y4_Y8_AGE_EXPOSURE_COMPARISONS.csv`;
- `Y4_Y8_AGE_EXPOSURE_PAIRWISE.csv`;
- `Y4_Y8_AGE_EXPOSURE_SYMMETRIC.md`;
- `Y4_Y8_BREADTH_DETERMINATION.md`;
- `Y4_Y8_SYMMETRIC_RESULT.json`.

## Exact reused rolling policy evidence

Prior workflow:
- run: `36271080037`;
- artifact: `10916355135`;
- digest: `sha256:63520ddb60a8ed12724fa21e8d276c4e3e7d5587162aade92ba7afaa3796ced2`.

Evidence:
- 11,940 player-origin rows;
- 47,760 policy prediction rows;
- exact common keys;
- policies: baseline, hard router, soft stack, blanket 75/25.

No row population was changed during symmetric interpretation.

## Exact reused age/exposure evidence

Prior workflow:
- run: `36274823761`;
- artifact: `10917390703`;
- digest: `sha256:6920fc05926ff0dd4eb2ef955d3abba3dfbea86b98530b39869da96b265515f2`.

Symmetric audit:
- 59,700 persisted prediction rows;
- five already-frozen age/exposure variants;
- no refit.

## Downstream current-shadow evidence

The impact-magnitude interpretation reuses the prior governed 335-player current shadow:

- run: `36267757579`;
- artifact: `10913539274`;
- digest: `sha256:ee8abf0854b5d64f110413dca6699bce764bb7cbc48264d7becd588b7646c052`.

This shadow is not used to choose a Forecast policy. It is only used to quantify how much long-horizon trajectories can alter current ordering.

## Statistical method

Pairwise uncertainty:
- source-origin × player clustered Bayesian/exponential-weight bootstrap;
- 2,500 repetitions;
- exact common rows;
- primary metrics: MSE, MAE, top-tail MSE;
- safety/context metrics: bias, Spearman direction, 80%/90% coverage-gap behavior.

No incumbent replacement margin is used.

## Frozen guards

- production Forecast changed: **no**;
- production H3 changed: **no**;
- production Intrinsic changed: **no**;
- models refit during final interpretation: **no**;
- new model family added: **no**;
- current named players used for selection: **no**;
- prior soft-stack authority assumed: **no**;
- Y8 exact authority granted: **no**.

## Terminal state

The final Research conclusion is persisted in:
- `Y4_Y8_UNCERTAINTY_AND_DOWNSTREAM.md`;
- `Y4_Y8_FINAL_CONCLUSION.md`;
- `Y4_Y8_FINAL_RESULT.json`.

Requested terminal state:

**MANAGEMENT GATE — Y4-Y8 LONG-HORIZON AUTHORITY**
