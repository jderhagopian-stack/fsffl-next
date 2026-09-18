# FSFFL NEXT - Remaining-Information Gap Audit Checkpoint

Checkpoint date: 2026-09-18  
Authority: research only  
Directive: Pre-final-holdout research design check - no model fitting  
Status: **AUDIT COMPLETE - EXACTLY ONE FAMILY CLEARS - STOPPED BEFORE ANY NEW EXPERIMENT**

## 1. Recovered boundary

- Research branch: `research/future-state-resolution-phase34-resume`.
- Clean Stage 3 reproducibility checkpoint recovered first.
- Audit start head: `2d03ead0eec576cc51285796c3db55a7bdde1666`.
- `main` at audit start: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.
- PR #147 at audit start: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`.
- No model was fit. M1a was not altered. No M4/M5, final holdout, current-player sentinel, implementation, promotion, merge, or deploy action was performed.
- No named current player influenced the audit.

## 2. Required coverage / provenance matrix

| Candidate concept | PIT source/provenance | Seasons | Positions | Coverage | Overlap with existing model | Leakage risk | Experiment-worthy? |
|---|---|---|---|---|---|---|---|
| Multi-year consistency | Phase 2 seasonal production plus corrected PIT age/state residuals, each normalized at its own historical cutoff | Strict prior-two feature definable from persisted residual history beginning 2007 through 2022 | QB/RB/WR/TE | Official validation: Y2 678/1,209 = 56.1%; Y3 621/1,165 = 53.3%; each position has at least 79 complete prior-two rows per horizon | Partial but distinct: baseline has one-lag raw production; fixed route has one-lag C memory only for QB; M3a tested directional trajectory, not prior-only level/stability | Low with frozen t-1/t-2 PIT residuals | **YES** |
| Role quality / role security | Current opportunity is governed; canonical rich-I1 roster/participation facts have historical research provenance; richer share/route/red-zone/depth/contract families are not governed in the Stage 0 panel | Mixed / not sufficiently verified for a distinct new family | QB/RB/WR/TE where canonical facts apply | Current opportunity 100% in Stage 0 preferred cells; M3b opportunity-delta 72.7%-74.4%; no verified coverage matrix for a distinct richer role-quality family | High overlap for opportunity and roster/participation continuity; richer concepts are unavailable/unverified | Low for dated existing facts; high/unknown for retrospective reconstructions | **NO** |

## 3. Family A - multi-year production consistency

### Why it is not merely C or M3a again

The existing Forecast already carries current and immediately prior raw fantasy points plus their difference. Phase 2 Q3 tested one immediately prior age/state-adjusted residual after controlling for current residual. Phase 3/4 C then used one prior age/state residual plus coverage in only prime/aging QB and aging WR/TE probability models; fixed position routing retained C only for QB.

Stage 3 M3a tested a different concept: directional current-minus-prior residual change plus a two-year slope.

A clean multi-year consistency test can therefore isolate **prior-only track-record level and stability**:
- it does not reuse the current residual owned by M1a;
- it does not encode direction/current-to-prior change owned by M3a;
- it does not add another raw prior-production transform;
- it does not alter A2 age or D current-state location;
- for QB it adds information beyond C's single prior residual by incorporating the second prior season and consistency across the two.

### Support

Official Stage 3 validation-row support for two genuine prior residual seasons:

| Horizon | QB | RB | WR | TE | Total |
|---|---:|---:|---:|---:|---:|
| Y2 sources 2020-2021 | 88/153 (57.5%) | 194/344 (56.4%) | 249/461 (54.0%) | 147/251 (58.6%) | 678/1,209 (56.1%) |
| Y3 sources 2019-2020 | 79/145 (54.5%) | 179/330 (54.2%) | 225/442 (50.9%) | 138/248 (55.6%) | 621/1,165 (53.3%) |

Development-era source seasons 2014-2018 also have substantial support: prior-two coverage is 61.8% QB, 53.3% RB, 52.9% WR, and 53.6% TE.

A third prior season is materially thinner: validation coverage falls to roughly 38%-46% by position, with only 62 Y3 QB rows. The audit therefore does **not** recommend a separate three-year coefficient family.

### Proposed one bounded experiment - NOT EXECUTED

Working baseline: fixed routed Forecast + frozen M1a.

Conditional production only; persistence and state-transition probabilities remain frozen.

Predeclare exactly:
- `prior2_mean_age_state_z = mean(z[t-1], z[t-2])`;
- `prior2_abs_gap_age_state_z = abs(z[t-1] - z[t-2])`;
- explicit `prior2_coverage`; uncovered continuous values use neutral zero with the coverage flag.

No current residual, no trajectory slope/direction, no repeated-elite threshold, no hard production tier, no age/stage interactions, and no named-player selection.

Use regularized global effects with position deviations only; no position x age x trajectory cells. All four positions exceed 79 complete prior-two validation rows in each horizon block.

Use the same Stage 3 chronological validation and uncertainty procedure. Freeze this representation before any result is viewed. The final holdout remains untouched unless a later directive explicitly authorizes this experiment and then the final exam.

## 4. Family B - role quality / role security

M3b's narrow opportunity-change result does **not** prove broader role security is useless. However, the audited evidence does not support another clean role-quality experiment now.

- Current opportunity per game and role band are fully governed but already part of the frozen reduced Forecast, and M3b tested their one-year change. Re-encoding them would double count.
- Roster continuity / organizational attachment and participation are already explicit canonical rich-I1 primitives: roster weeks/shares, last-status facts, status/team changes, return/entry counts, participation weeks, stats weeks, and snap-play weeks. Treating those as a new role-security family would largely duplicate an existing Forecast primitive.
- The authoritative Stage 0 production-resolution panel does not contain governed historical snap share, routes, route participation, target/carry share, red-zone role, workload competition, or depth-chart rank.
- NFL draft/team investment is not frozen as a governed historical Forecast coordinate in this workstream. The panel carries entry-season information for experience, not a governed pick/round investment feature.
- No governed historical contract/roster-control archive is present in the audited evidence.
- Exact Stage3-aligned historical coverage for a distinct richer role-quality family cannot be verified from the persisted production-resolution artifacts.

Therefore the family fails the audit bar because the verifiable pieces are either already modeled or the distinct pieces lack verified PIT provenance/coverage. No retrospective backfill is permitted.

## 5. Decision

**Audit outcome: EXACTLY ONE FAMILY CLEARS THE AUDIT BAR.**

Management next action under the directive:
- one bounded multi-year consistency experiment may be considered for explicit approval;
- do not execute it yet;
- do not open a role-quality/security experiment from the presently audited evidence;
- preserve the final holdout.

## 6. Reproducibility

Persisted machine-readable audit:
`artifacts/research/production_resolution/REMAINING_INFORMATION_GAP_AUDIT_2026-09-18.json`

Input hashes:
- Phase 2 player-season panel: `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`
- Phase 2 corrected Q3 rows: `9c504c9e765bd113406b59185a3cc80d23cca2401ecf31857692e15720b29063`
- Clean Stage 3 full audit: `22ba1638fb7e86146ad228c6d803c9ff1693d19f9dd36744bdefe0de37204767`

Relevant repository blobs:
- Stage 0 checkpoint: `47b3c2f90e4c01e2ddf0fa31a4bfa5100b7a6cf5`
- Clean Stage 3 checkpoint: `264268e566e521ce2316294e60942a8cfae6ddcf`
- Phase 2 Q3 method addendum: `d4a836cb74a38600c327a6d2fd1647dd39ed1650`
- Phase 3/4 protocol: `b5d14e115061a5fd52120400819be6929b520096`
- Integrated I1: `b5f181f56dbeaec8a353e9555e236c93a92cc3b3`
- Canonical football-state contract: `04aea2fd09cd745e02e8694d9232e86d037b743d`
- Production-source readiness matrix: `1b20a0924b0afa6e3971586a38d4df978c438de0`

## 7. Stop boundary

**STOP.** This audit did not fit a new model or inspect a new candidate result. Do not run the proposed consistency experiment, M4/M5, final holdout, current-player sentinels, implementation, promotion, merge, or deployment without a new explicit authorization.
