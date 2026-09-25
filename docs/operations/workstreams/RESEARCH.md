# Workstream — Forecast Research: 2026 Late-Start K/DST Exception

## State
**DIRECTIVE COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY**

Authorized: 2026-09-25  
Completed: 2026-09-25  
Implementation-ready handoff: `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`  
Current-date source ledger: `artifacts/research/k_dst_late_start_exception_20260925/SOURCE_ACQUISITION_LEDGER.json`  
Prior empirical/source closeout: `artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_CLOSEOUT.md`

## Management direction

Management authorizes investigation and implementation planning for a **one-season-only 2026 late-start K/DST Forecast baseline** using qualifying independent current season-long/rest-of-season projections acquired at the actual current date.

Binding:
- preserve exact acquisition timestamp, source provenance, projection horizon and source-health evidence;
- never represent late-start evidence as preseason;
- never backdate;
- any 2026 K/DST preseason comparison requiring unavailable pre-Week-1 evidence remains unavailable;
- beginning in 2027 the normal governed annual preseason snapshot process applies with no late-start exception;
- separately determine whether historical evidence supports bounded empirical K/DST uncertainty;
- never invent or borrow an unsupported uncertainty coefficient;
- retain existing two-source, independence, active-rule-completeness, source-health and anti-double-counting governance.

## Final research outcome

### What the 2026 exception changes

The absence of a qualifying 2026 pre-Week-1 K/DST snapshot is **no longer a current-forward Forecast blocker**.

A new 2026-only artifact may truthfully represent a current-date rest-of-season baseline if it preserves its real acquisition time and provenance.

It may not:
- satisfy the annual preseason snapshot contract;
- be called preseason;
- be used for a preseason-vs-current comparison;
- be backdated;
- become a generic fallback for 2027+.

### Current source acquisition

Research inspected current 2026 ROS/source surfaces and persisted exact acquisition evidence in the source ledger.

Key dispositions:
- **CBS:** current 2026 ROS K/DST candidate; useful raw coordinates; Friday-morning ATL/GB rows were stale after Thursday's completed game and require subject-row quarantine; K collapses 50+; D/ST PA is aggregate rather than a game-level bucket distribution.
- **LineupExperts:** current 2026 ROS candidate and plausible independent internal projection system; public rows also showed stale ATL/GB remaining-game counts; website extraction is prohibited, while a subscribed API path exists and requires rights/schema validation.
- **RotoWire:** current 2026 ROS product is semantically healthy; usable values/schema are paywalled/licensed; visible K schema still collapses 50+.
- **Razzball:** quarantined for wrong-year/impossible-game-count content.
- **FFToday:** current accessible 2026 K/DST season material remains preseason/full-season and is not eligible for the current-date ROS exception.
- **SportsDataIO:** season-long projections are documented as preseason-only; maintained in-season product is game-level and therefore outside this Management-authorized ROS path unless separately authorized.
- **FantasyPros:** ROS projection access exists under API/commercial products, but its aggregate projections cannot automatically count as an independent second vote.

### Source-health architecture

The late-start path requires **subject-row health**, not just provider-global health.

At capture time, implementation must compare each row's projected-games/horizon semantics against the canonical remaining NFL schedule.

Example:
- after Atlanta–Green Bay completed Thursday 2026-09-24, a Friday source row still carrying 15 remaining games for ATL/GB is stale and must be quarantined;
- a team that has not yet played Week 3 may still truthfully have 15 remaining games.

Never backdate or heuristically subtract a completed game's projection to make a stale row pass.

### Hodor K current-forward authority

**STILL BLOCKED.**

Exact transforms allowed:
- Hodor scores both 0–19 and 20–29 at 3 points, so an exact provider 0–29 made coordinate is sufficient for that combined scoring contribution.
- generic misses may be derived as FGA − FGM only when both are complete same-horizon provider evidence.
- XP misses may be derived as XPA − XPM under the same condition.

Still missing:
- Hodor separately scores 50–59 at 5 and 60+ at 6;
- healthy current candidate sources found by Research expose 50+ rather than a separate 60+ projection;
- no heuristic split is authorized.

Thus current Hodor K fantasy points cannot yet receive full active-rule authority.

### Hodor D/ST current-forward authority

**STILL BLOCKED.**

Current ROS candidates overlap on sacks, INT, FF and FR and some defensive TD/safety evidence.

Still missing two-source rule-complete authority for:
- blocked kicks;
- defensive two-point returns;
- team special-teams TD;
- team special-teams FF/FR;
- exact PA bucket expectation.

Aggregate season ROS PA or PA/game is not sufficient:
`score(E[PA]) != E[score(PA)]` for nonlinear buckets.

A provider-native or separately governed remaining-game PA distribution is required.

### K/DST uncertainty

**Historical evidence is sufficient to run a bounded empirical study; it is not sufficient to declare a production Hodor-total coefficient without executing and validating that study.**

Evidence available:
- genuine pre-opener 2024 multi-provider raw K/DST corpus;
- source-separated historical weekly K/DST projection panels;
- realized K/DST outcome reconstruction path;
- merged non-promoting PR #215 calibration harness.

Required bounded implementation:
1. define a `CalibrationScoringFingerprint`;
2. score historical provider projections only on coordinates that >=2 independent PIT providers actually support;
3. reconstruct realized outcomes under that exact fingerprint;
4. fit K and D/ST separately;
5. persist sources, seasons, sample sizes, hashes/provenance and diagnostics;
6. validate replay/holdout behavior;
7. compare the calibration fingerprint to the target league scoring fingerprint;
8. promote only if compatibility is proven.

A reduced standard K or D/ST subscore coefficient must not silently become Hodor-total uncertainty.

**No K/DST uncertainty coefficient is promoted or authorized by Research.**

### Rights

Management's model exception does not override external source terms.

Deployed/private-beta ingestion remains source-rights gated where public terms do not permit the intended automated/storage use.

Commercial production remains separately gated on explicit provider agreements for the actual content/storage/derived-output architecture.

## Gate decomposition

### Current-forward 2026 blockers
Still blocking governed Hodor K/DST Forecast:
1. rights-cleared deployable provider access;
2. >=2 independent sources per required active metric/group;
3. K exact 60+ evidence;
4. D/ST game/distributional PA bucket evidence and remaining rare-event coordinates;
5. promoted target-compatible K-specific and D/ST-specific empirical uncertainty.

### No longer a current-forward blocker
- missing 2026 preseason K/DST snapshot;
- inability to produce a true 2026 preseason-vs-current K/DST delta.

### Historical/preseason-only
- 2026 K/DST preseason comparison remains unavailable where authentic pre-Week-1 evidence does not exist.

### Commercial-only/external
- executed commercial licenses and sublicensing clarity for the eventual production provider set.

## Implementation contract

The authoritative implementation plan is:
`artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`

It requires:
- dedicated 2026-only late-start artifact, separate from annual preseason;
- `ForecastHorizon.REST_OF_SEASON`;
- immutable capture/provenance/source-health metadata;
- schedule-aware subject-row freshness;
- K and D/ST canonical normalization;
- exact-only scoring transforms;
- existing two-source/independence governance;
- no provider-native FPTS shortcut around raw rule coverage;
- scoring-fingerprint-bound uncertainty calibration;
- explicit 2026 preseason-unavailable presentation state;
- hard rejection of the exception for 2027+.

## Operating-protocol closure

The requested Management investigation and implementation planning are complete.

Further generic public-source searching is no longer the next authorized high-value action. Remaining source questions require licensed/API schema access, while uncertainty requires bounded implementation/execution of the already specified calibration plan.

No production implementation, Forecast promotion, merge, deployment, or uncertainty coefficient change was performed by Research.

**DIRECTIVE COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY**
