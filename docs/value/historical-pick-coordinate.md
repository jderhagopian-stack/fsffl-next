# Historical Pick Coordinate in FSFFL NEXT

## Purpose

Reconstruct the economic coordinate of a rookie pick at a historical timestamp using only evidence knowable at that time.

This is a Value-layer research capability. It does not create a new value channel and does not move authority into Historical Trade Analytics.

## What was retained from legacy research

The prior FSFFL research in `sleeper-league-data` PR #192 established several useful safeguards:

- no future rookie-draft/player leakage;
- no use of present-day pick values as historical truth;
- unresolved picks remain probabilistic;
- exact slots may be used only after evidence shows they were known;
- future-pick time adjustment is explicit rather than silently embedded;
- uncertainty and provenance are preserved.

NEXT keeps those principles while replacing league-specific assumptions with generic contracts.

## What was deliberately not ported

The legacy research hardcoded a 12-team league, three rookie rounds, FSFFL-specific evidence labels, a particular team-strength-to-slot transform, and fixed 0.80/0.90/1.00 horizon sensitivity rails.

None of those are universal model truths. NEXT therefore does not hardcode them.

League size and rookie-draft rounds come from `LeagueRules`. Slot probabilities are explicit upstream evidence. Horizon adjustment has no default. Historical slot observations carry their own value scale, timestamp, model version, and provenance.

## Input contract

`HistoricalDraftSlotObservation` records a historical draft-slot value frozen when that observation became knowable.

`HistoricalSlotProbability` records a point-in-time slot distribution generated upstream. The Historical Pick Coordinate does not infer team strength or create slot probabilities itself.

`HorizonAdjustment` is optional and explicit. If absent, the coordinate applies no time discount. A governed or research adjustment must identify its version and provenance.

`HistoricalPickCoordinateEvidence` binds those inputs to a canonical `DraftPick` and historical `as_of` timestamp.

## Leakage firewall

The coordinate rejects:

- draft-slot observations with `available_at > as_of`;
- slot probabilities with evidence after `as_of`;
- an exact slot whose known timestamp is after `as_of`;
- slot probabilities outside the configured league team count;
- picks outside the configured rookie-draft rounds.

It also fails closed when a probability-bearing slot has no historical slot-value evidence. It does not silently substitute a round median or current value.

## Value construction

For each historical slot, prior observations on the same explicit `ValueScale` are combined using mixture moments. The unresolved pick distribution is then passed to the existing NEXT `estimate_pick_value` primitive.

This deliberately reuses the existing Pick Value authority rather than building a second pick valuation implementation.

## Evidence quality

The first contract reports conservative evidence quality:

- `HIGH`: exact historical slot plus at least two prior draft seasons of evidence;
- `MEDIUM`: unresolved slot distribution plus at least two prior draft seasons;
- `LOW`: reconstructed from only one prior draft season;
- `INSUFFICIENT`: missing required slot probabilities or slot-value evidence;
- `EXCLUDED`: outside configured league rookie-draft semantics.

These labels describe evidence coverage, not a letter grade or production promotion decision.

## League-specific calibration exclusions

A particular league may mark a season or draft as ineligible historical rookie-pick evidence through the evidence-building workflow. For FSFFL research, the 2022 startup is such an exclusion because its picks were nomination/order mechanics rather than rookie-pick valuation evidence.

That exclusion belongs in FSFFL's dataset/configuration. It is not hardcoded in the generic coordinate.

## Next research steps

1. Build generic historical draft-slot observations from archived point-in-time Value evidence.
2. Build a governed upstream slot-probability research model from historical State/Forecast evidence.
3. Compare alternative horizon adjustments through temporal holdout rather than choosing a fixed discount by intuition.
4. Persist coordinate artifacts using the Historical Persistence dependency model.
5. Feed successful `PickValueEstimate` artifacts into the Historical Trade Grader through normal Value -> Decision paths.
