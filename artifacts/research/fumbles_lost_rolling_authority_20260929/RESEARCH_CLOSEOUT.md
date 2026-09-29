# Rolling FUMBLES_LOST Authority — Final Research Closeout

Date: 2026-09-29

## Terminal state

**DIRECTIVE COMPLETE — RESEARCH**

The bounded FUMBLES_LOST authority work is complete, including the PR #297 population-materiality correction and the full season-start/annual-rollover lifecycle.

## What remains unchanged

The accepted first-party rolling point model remains exactly the Week-2→17 contract previously validated:
- same exact lost-fumble semantics;
- same position-level opportunity-rate model;
- same four-pseudo-game role prior;
- same cutoff scalars;
- same rolling point-model uncertainty floors;
- no new Forecast family or cutoff router.

The original rolling validation remains authoritative:
- run `36525451903`;
- artifact `11014727753`;
- digest `sha256:eac8dffa80df5ba9adb6b279267b5c05134fefcbda71146b058fa837dec91db8`.

## PR #297 P1 correction

The original materiality fallback was too broad because its empirical bound excluded true cold starts.

The corrected fallback:
- uses a position-wide historical maximum over all completed prior player-seasons;
- can only widen the original bound;
- is explicitly validated by evidence tier;
- requires known/non-conflicting position for identity-light use;
- fails closed for **QB cold-start and QB identity-light at Weeks 13-17**.

The first corrected validation found the reason for that restriction:
- QB cold-start Week 13: 8/9 = 88.9%, below the frozen 90% coverage gate.

Research did not increase the bound post hoc. It restricted the unsupported late-season population instead.

After that restriction, every fallback-eligible observed population/cutoff clears the 90% gate.

Final lifecycle/materiality validation:
- run `36558353289`;
- artifact `11028911683`;
- digest `sha256:d37986d48f734b8d4a0882703bb6a90241eae0306b84c5a0083f3cd8db589768`.

## Season-start authority

Completed Week 0:
- no first-party FUMBLES_LOST point estimate;
- explicit omission;
- corrected `NON_MATERIAL_PARTIAL` allowance only when eligible and immaterial.

Completed Week 1:
- same behavior;
- Week-1 opportunities do not create unvalidated point authority.

Completed Week 2:
- transition into the already-supported rolling point model.

Week 18:
- no fabricated remaining-season point estimate.

No fake zero and no full-coverage claim at any omission state.

## 2027+ annual rollover

No broad annual model-family study is required.

Each target season gets a deterministic refresh followed by a **minimal governed freeze**:
- append finalized prior-season exact weekly evidence;
- recompute cumulative position rates and player role priors;
- recompute the same global Week-2→17 cutoff calibration ratios;
- never narrow prior uncertainty floors; widen with the newly completed held-out season when necessary;
- never narrow prior materiality bounds; widen with the newly completed all-population historical maximum when necessary;
- revalidate fallback population eligibility;
- fingerprint and freeze the target-season table before point authority.

If that bounded annual freeze fails, no automatic point authority is granted. The coordinate remains explicitly omitted and may proceed only through a valid materiality allowance; otherwise fail closed.

## Durable package

`artifacts/research/fumbles_lost_rolling_authority_20260929/`

Authoritative implementation inputs:
- `ROLLING_PRODUCTION_TABLE.json`
- `MATERIALITY_RULE.md`
- `SEASON_START_LIFECYCLE.md`
- `ANNUAL_ROLLOVER_CONTRACT.md`
- `IMPLEMENTATION_HANDOFF.md`
- `LIMITATIONS_AND_REPRODUCIBILITY.md`
- `FINAL_RESULT.json`
- `lifecycle_validation/*`

The original `PROTOCOL_FROZEN.md` remains preserved as the audit record of the first rolling/materiality formulation. Its primary-population materiality bound is superseded by the corrected v2 materiality contract.

## Boundaries preserved

No change to:
- Y2/Y3;
- Y4-Y7;
- K/DST;
- Intrinsic mathematics;
- #294/#295/#296 runtime architecture.

## Next action

Implementation may consume this frozen package immediately, update PR #297/merge the Research authority, implement the bounded lifecycle on the existing #296 lineage, and resume hosted lifecycle acceptance.

No additional Research decision is required.
