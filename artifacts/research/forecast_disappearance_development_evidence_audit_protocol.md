# FSFFL NEXT — Forecast disappearance vs development evidence audit

Research only. No merge or promotion. This artifact freezes only the Phase 1/2 evidence audit before any new C2/C3 challenger is defined or evaluated.

## Frozen purpose
Determine which strictly point-in-time football evidence can legitimately distinguish disappearance/non-persistence from temporary low production and legitimate development, and determine what a missing future row can and cannot mean in the existing historical panel.

## Sources to audit
1. The exact historical seasonal production source already used by `scripts/extract_career_transition_panel.R`: `player_stats_seasonal.RData` from the Fantasy Football Analytics Textbook repository.
2. The exact player identity source already used by that panel: nflverse `players.csv`.
3. The existing governed Forecast contracts/calibration code at the PR #141 research base.

No market, transaction, ownership, owner-behavior, roster-need, Value, or named-player evidence is permitted.

## Candidate evidence families
Audit, do not assume availability: current production, games/starts, pass attempts, rush attempts/carries, targets, receptions, touches if directly present, snaps/snap share, routes/route participation, age, experience, position, draft year/round/pick, and current governed production state. For every source field report exact source column, season and position coverage, earliest/latest reliable season, missingness, PIT semantics, and Forecast-authority fit.

A role/opportunity family is eligible for a C3 challenger only if direct football usage evidence is present with at least 90% nonmissing coverage in every position to which the chosen role definition applies across every final validation fold. Do not manufacture a proxy to meet this gate. If no common family meets it, C3 is not constructed.

## Missing-row semantic audit
For each chronologically observable h=1/h=2 target: distinguish target-row present, explicit zero-production row, missing target followed by later observed return, and missing target with no later row through available history. Targets beyond the observed panel edge are censoring and are not disappearance labels. Later return may be used only as an evaluation/label diagnostic, never as a live predictor.

The panel alone cannot prove NFL roster exit, injury/IR, suspension/NFI, or upstream source failure unless an independent strict-PIT source establishes that status. These categories must remain unresolved rather than inferred.

## Stop rule
This audit does not score C2/C3 and does not choose a model. After its evidence is reviewed, the challenger set, cohort definitions, smoothing/fallbacks, thresholds, seed, guardrails, and selection rule must be frozen in a separate protocol before any final challenger results are inspected.