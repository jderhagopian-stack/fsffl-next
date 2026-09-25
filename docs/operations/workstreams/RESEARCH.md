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

**STILL BLOCKED, but technical exact-rule feasibility is now proven for one provider candidate.**

Exact transforms allowed:
- Hodor scores both 0–19 and 20–29 at 3 points, so an exact provider 0–29 made coordinate is sufficient for that combined scoring contribution.
- generic misses may be derived as FGA − FGM only when both are complete same-horizon provider evidence.
- XP misses may be derived as XPA − XPM under the same condition.

Still missing:
- Hodor separately scores 50–59 at 5 and 60+ at 6;
- healthy current candidate sources found by Research expose 50+ rather than a separate 60+ projection;
- no heuristic split is authorized.

JerryGM's deployed API documentation now proves a current 2026 ROS source can price a distinct `fg60plus` rule. Its public raw stat-line schema does not independently expose a 60+ component, so live API validation is required to determine whether a rule-specific breakdown can satisfy FSFFL's governed distributional-evidence contract.

No second independent current ROS source was found publicly proving that 60+ coordinate.

Thus current Hodor K fantasy points cannot yet receive full active-rule authority.

### Hodor D/ST current-forward authority

**STILL BLOCKED, but technical PA-distribution feasibility is now proven for one provider candidate.**

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

**Bounded empirical uncertainty has now been measured on explicit reduced fingerprints; Hodor-total promotion remains blocked.**

Durable empirical artifact:
`artifacts/research/k_dst_late_start_exception_20260925/EMPIRICAL_UNCERTAINTY_CHECK.md`

2024 K reduced fingerprint:
`3*FGM - (FGA-FGM) + XPM`
- 34 kickers;
- >=2 PIT providers per sample;
- season relative RMSE **0.3841884793**;
- 542 weekly kicker observations / 42 subjects;
- weekly pooled CV **0.5223274618**.

2024 D/ST reduced fingerprint:
`1*DST_SACK + 2*DST_INTERCEPTION`
- 30 defenses;
- >=2 PIT providers per sample;
- season relative RMSE **0.2140283312**;
- 544 weekly team observations / 32 subjects;
- weekly pooled CV **0.6381941339**.

These measurements clear the question of whether bounded empirical K/DST uncertainty can be estimated at all.

They do **not** authorize Hodor-total coefficients because the target includes active coordinates outside the fitted fingerprints, including K 60+ and D/ST PA buckets/rare events.

Required implementation:
1. encode `CalibrationScoringFingerprint`;
2. reproduce the retained measurements;
3. add replay/holdout diagnostics;
4. govern uncertainty for every excluded target coordinate;
5. promote only when full target compatibility is proven.

**No Hodor-total K/DST uncertainty coefficient is promoted or authorized by Research.**

### Exact-capability current source finding

JerryGM is the strongest technically aligned source found under this directive:
- 2026 `week=current&horizon=ros`;
- K custom scoring includes 50-59 and 60+ separately;
- D/ST includes blocks, two-point returns and a modeled points-allowed spread;
- `paTierExpectedPPG` integrates arbitrary PA tiers over that spread.

However:
- a live API key is required to validate current payload health/content identity;
- JerryGM's internal model variants count as one provider ecosystem;
- its terms prohibit using API output to train/calibrate a competing projection product, so FSFFL ensemble use requires written provider clarification/partner terms.

No second public provider was found proving both the Hodor 60+ K coordinate and distributional D/ST PA-tier evidence.

### Rights

Management's model exception does not override external source terms.

Deployed/private-beta ingestion remains source-rights gated where public terms do not permit the intended automated/storage use.

Commercial production remains separately gated on explicit provider agreements for the actual content/storage/derived-output architecture.

## Gate decomposition

### Current-forward 2026 blockers
Still blocking governed Hodor K/DST Forecast:
1. rights-cleared deployable provider access;
2. >=2 independent sources per required active metric/group;
3. K: live validation of the first exact 60+ candidate plus a second independent 60+ source;
4. D/ST: live validation of the first PA-distribution candidate plus a second independent PA-distribution source and remaining rare-event two-source coverage;
5. target-compatible K-specific and D/ST-specific empirical uncertainty promotion.

Historical uncertainty evidence itself is no longer absent; reduced-fingerprint empirical measurements now exist.

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
