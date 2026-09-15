# FSFFL NEXT - Event-Time Roster / Transaction + Absence-Cause Evidence Reconstruction Protocol

RESEARCH ONLY. Evidence reconstruction only. Do not merge or promote. No Forecast calibrator, Value/Shapley change, B4 change, Constitution change, C4, or production-authority change.

## Starting state frozen before substantive analysis

- production `main`: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #139 head: `ff534c52e8e9694ebdae7f48df209ada0cc3f555`
- PR #140 head: `002afcd5b6d25ade12317a563330658a77791526`
- PR #141 head: `5a37d831ed759a76d26742e5295e863d150dbaf0`
- PR #142 head: `724ae9a6c6e9585702ffaf5808aaeb7e1af1bd3b`
- PR #143 head / research base: `6401d7b3d6fcdae3f6bdea6c3b0348881a2473e7`
- authoritative E2 workflow: `35002959309` (success)
- authoritative E2 artifact: `10411185876`, digest `sha256:0eec8bd6842a26052dbd435b7bc2d3caffc1ca7a3087cc9ccde580c7c9ad438c`

## Phase 0 reproduction gate

Before new evidence is interpreted, the retained PR #143 artifact must reproduce:

- 925 low-end missing target rows;
- 546 resolved factual contexts / 59.027027% resolution;
- 379 unresolved / 40.972973%;
- position-specific resolution and era-specific resolution;
- temporary-return vs persistent-disappearance context splits;
- prior strongest roster-continuity signals (`last_status_active`, `active_share`, `released_share`);
- prior source-family coverage.

If these do not reproduce exactly apart from serialization/rounding, STOP and diagnose.

## Evidence sources authorized for reconstruction

Primary machine-readable reconstruction uses nflverse/nflreadpy data only:

1. weekly NFL rosters/status (`load_rosters_weekly`) - GSIS-keyed, season/week effective bucket, available from 2002;
2. official weekly injury/practice reports (`load_injuries`) - GSIS-keyed, season/week plus `date_modified`, report/practice injury and status fields;
3. player weekly stats (`load_player_stats(..., summary_level="week")`) - GSIS player-week game participation/stat evidence where available;
4. snap counts (`load_snap_counts`) - PFR-keyed and mapped to GSIS through the nflverse player identity table;
5. player identity (`load_players`) - GSIS/PFR and other cross-IDs;
6. existing depth-chart evidence from PR #143 remains a secondary descriptive family.

Source-audit-only paths may include NFL.com official transaction pages, Sports Reference/PFR, licensed commercial APIs, and other public sources. They are NOT bulk-scraped in this study when their terms prohibit or leave automated/commercial use unresolved.

## Source-rights protocol frozen before results

- nflverse-data repository licensing is recorded as CC BY 4.0, while nflverse itself states that NFL data belong to their respective owners and remain subject to those owners' terms. Therefore nflverse-derived evidence is classed at most `PRODUCTION TERMS REVIEW REQUIRED` until management/legal review resolves the upstream-data issue.
- NFL.com direct systematic retrieval is prohibited for this study because NFL Terms limit use to individual non-commercial informational purposes and prohibit systematic retrieval/database compilation without prior written consent.
- Sports Reference/PFR direct automated extraction is prohibited for this study because its current terms restrict automated access/database substitution and AI/model uses without permission.
- Licensed commercial transaction feeds may be documented as an alternative production path but are not silently treated as available or cleared.

This is a governance assessment, not legal advice.

## Strict PIT semantics

Predictor-eligible factual evidence is limited to facts effective no later than the historical decision/source-season boundary. For this evidence-only study, target-season facts are used only to explain the retrospective missing-row outcome and are never converted into a live predictor. Future reappearance is outcome labeling only.

A weekly roster status transition is a week-effective organizational event, not an asserted exact calendar-date transaction. The reconstruction must preserve that granularity explicitly.

Absence from an injury report is not `healthy`. Absence from a roster row is not `released`. One missing production season is not `career over`.

## Frozen absence-cause taxonomy

Each low-end missing target row is assigned at most one primary factual category under the following fail-closed precedence. `UNKNOWN_UNRESOLVED` is preferred to unsupported inference.

1. `RETIRED` - explicit RET/retired factual status.
2. `SUSPENDED_OR_EXEMPT` - explicit SUS/EXE status.
3. `PUP` - explicit PUP status.
4. `NFI` - explicit non-football injury/reserve status (for example RSN where source semantics support it).
5. `IR` - only where the source explicitly distinguishes injured reserve; generic reserve status alone is insufficient.
6. `OTHER_RESERVE` - explicit generic reserve designation that cannot be safely refined to IR/PUP/NFI.
7. `PRACTICE_SQUAD` - explicit DEV/practice-squad retention.
8. `ACTIVE_ROSTER_INJURY_LIMITED` - organizationally attached on ACT/INA (or equivalent non-reserve active-contract status) and official weekly injury/practice evidence demonstrates limitation; this explicitly includes non-IR injury absence.
9. `ACTIVE_ROSTER_NO_PRODUCTION` - organizationally attached / active-contract evidence, no production, and no demonstrated injury cause. This does not assert health.
10. `WAIVED_OR_RELEASED` - explicit CUT/NWT/RFA/RSR/TRC/TRD/TRT or equivalent release status/event.
11. `UNSIGNED_OR_FREE_AGENT` - explicit UFA/free-agent status with no contradictory contemporaneous attachment evidence.
12. `TEAM_TRANSITION_TRANSACTION_IN_FLIGHT` - factual team change/status transition that preserves or re-establishes organizational attachment but does not fit a more specific category above.
13. `TEMPORARY_ABSENCE_OTHER_FACTUAL` - other documented temporary unavailability not captured above.
14. `UNKNOWN_UNRESOLVED` - insufficient or conflicting evidence.

Target-season evidence takes precedence for explaining the missing target season. If no target-season row exists, the source-season terminal status and source-season status/team transition history may provide factual context, but must not be upgraded beyond what the status semantics support.

## Mandatory non-IR injury object

For each relevant player-week, retain factual fields where available:

- GSIS player id;
- season/week;
- rostered team and roster status;
- practice status;
- report status;
- primary/secondary injury text where source-governance permits;
- game participation/stat-row presence;
- snap participation where available;
- active/inactive organizational status;
- PUP/NFI/reserve/suspension/practice-squad flags;
- team/status transitions from prior observed week;
- evidence provenance and source granularity.

A non-IR injury-limited week requires official injury/practice evidence plus continuing organizational attachment without an explicit PUP/IR/NFI classification. An inactive/missed-game week with no demonstrated injury remains distinct from injury-limited absence.

## Event-time transaction reconstruction

The machine-readable transaction proxy is deterministic weekly status/team transition history from weekly rosters. Derived factual event labels may include `TEAM_CHANGE`, `STATUS_CHANGE`, `RELEASE_STATUS_ENTERED`, `PRACTICE_SQUAD_ENTERED`, `RESERVE_ENTERED`, `PUP_ENTERED`, `NFI_ENTERED`, `SUSPENSION_ENTERED`, `ACTIVE_RETURN`, and `ATTACHMENT_REESTABLISHED`. These are week-effective transition facts, not exact-date transaction claims.

Exact-date transaction sources are audited separately for availability and rights. No restricted source is scraped merely to improve the result.

## Descriptive outcome comparisons

Future return and true-developmental status are retrospective labels only.

Required descriptive comparisons:

- missing target + later return vs missing target + no later row;
- true-developmental vs persistent disappearance;
- full taxonomy by position and era;
- non-IR injury enrichment among temporary-return cases;
- roster/status, transaction-transition, injury/availability, practice/reserve, depth and snap families.

No Forecast model, transition probability, Brier comparison, Shapley run, anticipated-production change, or named-player tuning is permitted.

## Incremental-information diagnostic frozen before results

This is interpretation-only and cannot define a Forecast challenger.

A new family beyond the known aggregate roster-continuity family is considered materially nonredundant if all of the following are demonstrated:

1. it is not algebraically derived from `active_share`, `last_status_active`, or `released_share`;
2. within at least one roster-continuity stratum (`last_status_active=1` or `last_status_active=0`), it shows either:
   - absolute AUROC separation >= 0.58 for a continuous/binary factual feature with at least 30 true-developmental and 60 persistent-disappearance observations in the stratum; OR
   - an outcome-group category-share difference >= 10 percentage points with at least 30 observations in each comparison group;
3. the direction of the descriptive difference is replicated in at least two positions or at least two eras when each replicated cell has at least 15 observations per outcome group;
4. for continuous features, absolute Spearman correlation with each of `active_share` and `released_share` is < 0.80, or the report provides a factual argument showing why the feature encodes distinct information despite correlation.

Failure to meet this diagnostic does not make the evidence useless; it means Gate E is not demonstrated.

## Era bins frozen before results

- early: 2012-2015
- middle: 2016-2019
- recent: 2020-2023 source seasons

No later-era-only restriction is permitted in the final conclusion.

## Evidence Gates A-H frozen before results

### Gate A - Factual resolution
PASS only if >=70% of the 925 baseline low-end missing rows receive a defensible non-UNKNOWN factual context under the frozen taxonomy.

### Gate B - Era safety
PASS only if all three frozen eras remain in the analysis, resolution is reported separately, and no era has <50% factual resolution. If an era is below 50%, FAIL and quantify the resulting all-fold limitation.

### Gate C - Position safety
PASS only if QB/RB/WR/TE are all retained, source coverage is reported for each, `UNKNOWN` is preserved fail-closed, and no position has >60% unresolved rows. RB is explicitly audited as the prior weakest position.

### Gate D - Temporary-absence distinction
PASS only if at least 5% of temporary-return missing rows are factually identified as non-IR injury-limited or another explicit temporary-unavailability category AND that share exceeds the corresponding persistent-disappearance share by at least 3 percentage points; reserve-list injury states must remain separately reported.

### Gate E - Incremental information
PASS only if at least one evidence family beyond aggregate roster continuity satisfies the frozen nonredundancy diagnostic above.

### Gate F - PIT integrity
PASS only if predictor-eligible source-period facts are timestamped/effective at or before the historical boundary, target/future facts remain outcome context only, and no future return/breakout label enters a predictor-side field.

### Gate G - Reproducibility
PASS only if reconstruction is deterministic, stable GSIS IDs are primary, PFR joins use an explicit identity map with unmapped/conflict rates reported, manual mapping count is reported, and no silent name-based predictive joins occur.

### Gate H - Commercial governance
Every required family must be classified as `CLEARED FOR RESEARCH ONLY`, `CONDITIONALLY GOVERNABLE`, `PRODUCTION TERMS REVIEW REQUIRED`, or `NOT SUITABLE`. PASS for model-study authorization means management receives a precise source-by-source governance path; it does not itself grant production clearance. If evidence quality clears A-G but a required family has no governable production path, final conclusion must be E3 rather than E1.

## Final decision rule

Conclude exactly one E1/E2/E3/E4/E5 from the management packet. E1 requires Gates A-G to pass and Gate H to present a credible governable path; it does not authorize a Forecast study automatically. E3 is used when evidence quality is otherwise adequate but required commercial-production rights are the blocking issue. No new research family begins after this workstream without separate management authorization.
