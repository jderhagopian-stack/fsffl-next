# FSFFL NEXT — Current Football-State H3 Update Research Protocol

Date: 2026-09-26  
State: **FROZEN BEFORE OUTCOME ANALYSIS / RESEARCH ONLY**

## Objective

Determine whether a governed current-football-state Forecast update layer is justified for H1-H3 after events such as injury/return, NFL team change, cut/signing, promotion/demotion, suspension/exempt status, retirement, and related role/availability shocks.

Production H3 is not changed by this study.

## Authority boundary

Event evidence belongs to Forecast.

Intrinsic may change only because an authoritative Forecast coordinate changes. No direct injury, trade, role, age, cut, suspension or retirement penalty may be applied inside Intrinsic.

## Questions

1. Which current-season effects are already reflected by governed current provider ROS projections?
2. What event evidence adds incremental predictive value beyond production/role baselines?
3. How much of an injury shock is:
   - current-season availability loss;
   - conditional production if active;
   - post-return role/opportunity;
   - recurrence/reinjury;
   - durable future survival/career effect?
4. How quickly should event influence decay across H1/H2/H3?
5. Which event types are too sparse/ambiguous for precise adjustments?
6. How can the system avoid double counting provider-revised Y1 evidence?

## Historical evidence

Use governed PIT football evidence only:
- nflverse weekly rosters, injury reports, snap counts and weekly player stats;
- governed career/production/usage panels already used by I1 research;
- canonical roster/injury/participation mappings from the frozen I1 research oracle.

No Market, fantasy ownership, dynasty value, owner behavior, fantasy trades or Team Utility inputs.

## Historical validation

### A. Event-rich versus reduced H1-H3 state Forecast

For chronological source-season holdouts, fit the existing I1 model family twice from only earlier fully resolved target seasons:
- **reduced**: age/career stage, experience, current/prior production and role/opportunity;
- **event-rich**: the same baseline plus canonical roster continuity, team/status churn, returns, release/practice/reserve/suspension evidence, injury-limited weeks and participation.

Evaluate separately at H1, H2 and H3:
- persistence Brier/log loss;
- six-state Brier;
- anticipated-production MAE/bias;
- conditional-production MAE among realized survivors;
- event-cohort metrics by position.

The event-rich path earns use only where it adds stable OOT information; the reduced path is a comparator, not presumptive authority.

### B. Injury episode decomposition

At weekly event time, require at least three prior active-game observations where possible.

Classify injury severity using only contemporaneous report/roster evidence:
- limited/questionable;
- doubtful/out;
- reserve/IR/PUP/NFI.

Classify broad injury family only from contemporaneous injury text where support exists.

Measure:
- remaining-season participation/availability;
- games-to-return;
- post-return fantasy points per active game relative to pre-event;
- post-return opportunity per active game relative to pre-event;
- recurrence after return;
- H2/H3 persistence and conditional production.

Temporary injuries must not receive a durable penalty unless OOT evidence shows persistent role/production/survival effects.

### C. Non-injury event study

Evaluate explicit/PIT:
- team change;
- release/cut;
- return/signing/reattachment;
- suspension/exempt;
- retirement;
- data-derived promotion/demotion from already-observed opportunity changes.

Measure current-season role/production persistence and future survival separately.

## Current provider-capture study

Capture current 2026 research-only ROS projections from the presently wired ROS sources where source health permits.

Compare current ROS expectations with the immutable 2026 preseason remaining-schedule prior for current players with canonical event evidence.

This is a current diagnostic, not a historical causal estimate.

Provider revision tables are currently empty, so this study must not claim a historical provider-revision time series exists.

## Double-counting rule

If healthy two-source current ROS Forecast is authoritative for H1:
- do not add an event penalty to the same H1 total;
- provider-updated ROS owns current-season availability + role/conditional-production expectation;
- event state may be retained as explanation/provenance and as an input to independently validated H2/H3 persistence/role models.

If current ROS authority is unavailable:
- a separately governed availability fallback may alter only the missing current-season availability component;
- it must not silently change conditional healthy production or future survival.

## Horizon semantics

No hand-coded decay curve.

Any persistence/decay must be horizon-specific empirical output from H1/H2/H3 validation.

## Required closeout

Return with:
- provider-capture evidence;
- event-rich vs reduced OOT results;
- injury decomposition;
- other-event diagnostics;
- supported update contract or negative finding;
- source/rights/provenance limitations;
- implementation-ready Forecast handoff only if evidence clears the bar;
- Management gate.

