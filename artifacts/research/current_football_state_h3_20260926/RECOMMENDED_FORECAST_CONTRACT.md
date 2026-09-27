# Recommended Current Football-State Forecast Contract

Date: 2026-09-27  
Status: **RESEARCH CANDIDATE / NO PRODUCTION CHANGE**

## Principle

Football-state changes trigger **Forecast reevaluation**. Intrinsic never applies an independent injury, trade, cut, role or suspension penalty.

The narrowest evidence-supported contract is componentized and source-aware.

## H1 — remaining current-season Forecast

### When a governed current-ROS Forecast is authoritative

Use the current ROS point Forecast as the H1 remaining-season expectation.

It owns the provider's integrated view of:
- remaining availability;
- role/opportunity;
- conditional active-game production.

**Do not add a second event haircut to those same H1 points.**

Current capture demonstrates why: among 58 provider-mapped injury players, median current ROS was **1.048×** the structural remaining-preseason comparator, not lower. A generic injury haircut would double count or contradict the provider view for many players.

### When current ROS authority is unavailable

Do **not** manufacture a generic injury/event multiplier.

The Forecast contract may expose a distinct `remaining_season_availability` component, but a numerical fallback may alter only availability when there is separately governed direct evidence of unavailability/eligibility. It must leave:
- conditional healthy production;
- H2/H3 survival;
- durable talent/quality
unchanged unless an independently validated model says otherwise.

The current historical study does not promote a general learned availability updater.

## Injury behavior

For a temporary/non-reserve injury:
- update H1 remaining availability only when governed evidence supports it;
- keep conditional healthy production unchanged by default;
- keep H2/H3 baseline unchanged;
- use event state as explanation/provenance.

For reserve/extended-unavailability:
- treat the availability state as materially different for H1;
- do not infer a fixed post-return or dynasty penalty;
- any role or H2/H3 change requires independently validated evidence.

Return from injury reverses the temporary availability state as current evidence changes. No separate Intrinsic reversal is needed.

## H2/H3 injury durability

No generic injury H2/H3 updater is promoted.

The full availability/participation layer failed the H2/H3 OOT gates, including injury-specific cohort audits. Recurrence and post-return descriptive differences remain explanatory only.

## Structural events

### Release / cut

This is the one narrow event-specific future-state signal that clears the frozen gate:
- H3 OOT n = **62** across four holdouts;
- persistence-Brier improvement = **2.61%** versus the reduced parent;
- state-Brier improvement = **0.70%**;
- point MAE worsens **1.93%**, within the frozen 5% degradation limit;
- persistence direction improves in all four holdout seasons.

No position subgroup reaches n>=30, so this supports only a **coarse H3 attachment/survival-risk state**, not a position-specific cardinal multiplier.

A release/cut event should therefore trigger Forecast reevaluation and may carry a coarse H3 persistence-risk indicator in a future promoted contract. It does not authorize a hand-coded point haircut.

### NFL team change

No generic trade bump or penalty is supported. Descriptive response is highly heterogeneous by position and the OOT organizational layer fails H1/H2 gates.

### Promotion / demotion

These events are defined from already-observed opportunity changes. They should trigger reevaluation of current role/projections, not a second additive role multiplier. The present study does not promote a separate H2/H3 coefficient.

### Reattachment / signing

No precise H2/H3 multiplier is supported.

### Suspension / exempt

Historical fitted sample is below the frozen 30-row minimum. Known current-season ineligibility may affect H1 availability directly, but no learned future multiplier is promoted.

### Retirement

The historical event sample contains one observed retirement event, insufficient for an empirical coefficient. Confirmed retirement should be represented as an explicit football-status/eligibility state if Management separately governs that semantic, not calibrated from this one-row study.

## Forecast output semantics

A future versioned Forecast contract should make these components explicit:

- `remaining_season_availability`
- `conditional_active_production`
- `post_return_or_current_role`
- `future_survival_or_attachment_state`
- `event_provenance`
- `provider_ros_identity`
- `double_count_guard`

Intrinsic consumes the resulting H1/H2/H3 expected-production coordinate only. It does not inspect event flags to apply its own penalty.

## Invalidation

When a promoted Forecast component materially changes, Forecast output identity/version changes. That change invalidates/recomputes Intrinsic through the existing dependency chain.

A football event by itself does not directly invalidate Intrinsic unless it changes an authoritative Forecast input/output.

## Current authority limitation

The 2026 research capture is not sufficient for broad current H1 production authority:
- CBS mapped 292 exact-standard rows;
- Razzball mapped 59 exact-standard rows;
- only **54 players** had exact two-source standard scoring;
- CBS/Razzball deployment rights remain uncleared.

Therefore this contract is a Research recommendation, not a source promotion.
