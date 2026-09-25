# Workstream — Forecast Research: K/DST + New-League Bootstrap

## State
**AUTHORIZED / NEXT**

## Objective
Produce an evidence-backed, implementation-ready governed Forecast architecture for leagues containing K and/or D/ST, while separately defining new-league Forecast bootstrap when no preserved preseason baseline exists.

## Authoritative starting facts
- Original FSFFL does not roster K or D/ST.
- A newly connected Sleeper league includes K/DST scoring/configuration.
- Performance has demonstrated durable league switching and working governed-refresh initiation.
- The new league currently fails closed in Forecast because qualifying live full-season evidence is insufficient and no preserved preseason Forecast baseline exists.
- Existing offensive-player Forecast authority must not be weakened merely to make this league load.

## Research questions
1. What K and D/ST configuration/scoring information is authoritative from Sleeper?
2. What raw historical and forward-looking evidence is available for K?
3. What raw historical and forward-looking evidence is available for D/ST?
4. Should K use a distinct forecast family from QB/RB/WR/TE? If so, define the contract.
5. Treat D/ST explicitly as an NFL team-unit fantasy asset; define its forecast contract and identity mapping.
6. Which current providers genuinely supply sufficient raw metrics for arbitrary supported league scoring, and with what provenance/source-health limitations?
7. How should uncertainty be represented and calibrated for each asset family?
8. How should replacement/scarcity/value consume these forecasts without contaminating Forecast authority?
9. What is the governed behavior when evidence is insufficient?
10. Separately: how should a league first connected after preseason obtain a valid Forecast baseline? Determine what can be reconstructed from league-agnostic stored/raw evidence and what cannot.
11. Identify any FSFFL-specific assumptions in Forecast interfaces exposed by this work.

## DO NOT
- Do not alter production model authority.
- Do not lower evidence thresholds just to turn a gate green.
- Do not fabricate K/DST projections.
- Do not route K/DST through offensive-player machinery without evidence that the semantics are valid.
- Do not let Behavioral/Team Utility contaminate universal Forecast or Value.
- Do not implement product UI.
- Do not merge/deploy model changes as part of research unless Management explicitly authorizes implementation.

## Required outputs
- source/provenance inventory;
- K forecast contract;
- D/ST team-unit forecast contract;
- scoring translation contract;
- uncertainty/calibration proposal with evidence;
- new-league bootstrap contract;
- synthetic league fixtures/test matrix;
- migration/compatibility notes for Forecast → Value → Simulation → Decision/Search;
- explicit unresolved risks and evidence gaps;
- implementation handoff with acceptance tests.

## Acceptance
Use `../ACCEPTANCE_GATES.md`. Research owns the outcome through an implementation-ready recommendation, not merely a literature/source survey.

## Operating behavior
Follow `../OPERATING_PROTOCOL.md`. Maximize each turn. If evidence contradicts the working hypothesis, investigate it. Stop only at DIRECTIVE COMPLETE, BLOCKED, MANAGEMENT GATE, or unavoidable turn continuation.
