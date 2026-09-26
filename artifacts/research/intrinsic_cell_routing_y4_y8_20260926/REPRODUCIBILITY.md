# Cell-Specific Y4-Y8 Intrinsic Research Reproducibility

Date: 2026-09-26

## Research branch

`research/intrinsic-cell-routing-y4-y8-20260926`

Corrected rolling-validation branch head:
`be2541a496227b33c12c755f576843dc4ab5a0bb`

Age/experience audit corrected head:
`d0ea8fff51a1d809bf2a392abfdc9bd2da045dec`

## Frozen policy inputs

- `CELL_ROUTING_POLICY_FREEZE.json`
- `CELL_ROUTING_POLICY_SPEC.md`
- `AGE_EXPERIENCE_AUDIT_FREEZE.json`
- `AGE_EXPERIENCE_AUDIT_SPEC.md`

The routing policy was frozen before repeated outer validation.
The age/experience/exposure audit was frozen before its results.

## Corrected rolling validation

Workflow:
`Intrinsic Cell Routing Rolling Validation`

- run: `36271080037`
- artifact: `10916355135`
- digest: `sha256:63520ddb60a8ed12724fa21e8d276c4e3e7d5587162aade92ba7afaa3796ced2`

The workflow restores only governed historical model/panel inputs. It does not restore the prior comprehensive final-holdout artifact.

The selector uses only earlier historical origins for each later outer origin. The prior exposed holdout is retained as diagnostic history but is not route-selection evidence.

Y8 has only two qualifying repeated outer origins after preserving at least three prior origins, so it is ineligible for exact-cardinal authority in this corrective.

## Age / experience / exposure audit

Workflow:
`Intrinsic Age Experience Exposure Audit`

- successful corrected run: `36274823761`
- artifact: `10917390703`
- digest: `sha256:6920fc05926ff0dd4eb2ef955d3abba3dfbea86b98530b39869da96b265515f2`

The first run failed before scoring because of an engineered-column alias mismatch. The correction changed only those column references; the frozen evidence, variants and interpretation contract were unchanged.

## Durable final summaries

- `ROUTING_POLICY_AGGREGATE.csv`
- `FINAL_CELL_ROUTING_STATUS.csv`
- `AGE_EXPERIENCE_POSITION_SUMMARY.csv`
- `FINAL_RESULT.json`
- `MANAGEMENT_HANDOFF.md`

The full per-player rolling prediction banks and detailed fold metrics remain retained in the workflow artifacts identified above.

## Authority safeguards

- Production H3 unchanged.
- No Y4-Y8 implementation.
- No current named-player tuning.
- No Market, dynasty value, Owner Intelligence, Team Utility or trade-acceptance inputs.
- No second untouched Y8 holdout claimed.
- No post-hoc hand repair of the previously failed blanket 75/25 architecture.
- No universal age penalty, youth bonus or workload wear coefficient introduced.
