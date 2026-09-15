# FSFFL NEXT — Strict PIT Role / Availability Evidence Reconstruction Protocol

Research-only. No model treatment. Do not merge or promote.

## Frozen objective
Determine whether richer historical factual NFL role/availability/roster-continuity evidence can be reconstructed with strict point-in-time provenance, adequate coverage, auditable identifiers, and sufficient descriptive separation to justify management considering a later bounded Forecast calibration study.

This workstream does **not** fit C4 or any Forecast challenger, alter C0/C1/C2/C3, change anticipated-production means, modify Value/Shapley/W, change B4 or the Intrinsic Constitution, use market/owner/team-utility evidence, or run downstream Shapley.

## Repository baseline
Research branch begins from frozen PR #142 head `724ae9a6c6e9585702ffaf5808aaeb7e1af1bd3b`. PR #139/#140/#141/#142 remain read-only. Production `main` is not modified.

## Evidence families to reconstruct
1. Weekly NFL roster status and team continuity — direct GSIS ID.
2. Weekly depth-chart rank — direct GSIS ID.
3. Game-level offensive snap counts/share — PFR ID joined to GSIS through nflverse player identity mapping.
4. Weekly official injury/practice-report evidence — direct GSIS ID.
5. Existing governed source-season production, age, experience and entry context from the frozen career-transition panel.

Participation/routes are audited for feasibility but are not required in the core reconstruction because their historical source changes and later-era licensing/availability create a distinct era contract.

## Strict PIT boundary
For descriptive discrimination, a source player-season uses only facts observable by the end of that completed NFL regular season. It is compared with next-season outcome groups solely for retrospective descriptive analysis. No next-season roster, injury, return, or breakout label may enter predictor-side evidence.

Next-season roster/injury/status records may be used only in the separate missing-row factual-context decomposition, where the target-row absence is already an observed historical outcome.

## Frozen descriptive cohorts
- LOW-END: positive source-season fantasy production at or below the position-specific 25th percentile using history through the source season.
- TRUE DEVELOPMENTAL: LOW-END + frozen YOUNG age band + next-season state usable-or-better.
- DEPTH PERSISTENCE: LOW-END + next-season state remains depth and the player remains observed.
- TEMPORARY ABSENCE / RETURN: LOW-END + next-season production row absent + a later production-panel row exists.
- PERSISTENT DISAPPEARANCE: LOW-END + next-season row absent + no later production-panel row observed.
- OLDER FRINGE: LOW-END + frozen AGING age band.

Age bands and five positive production-state boundaries reuse the already-frozen career-state research definitions. These are descriptive outcome groups, not model features.

## Descriptive methods only
Authorized: cohort tables, distributions, coverage tables, standardized mean differences, raw univariate AUROC, categorical proportions, position/era decomposition, missing-row factual-context counts, identifier-join audit.

Not authorized: predictive-model tournaments, coefficient fitting, threshold tuning against outcomes, treatment selection, Shapley/Value diagnostics, named-player tuning.

## Coverage / descriptive feasibility checks
These checks organize the evidence report; they do not create production authority.

A source family is considered broad in the 2012–2023 descriptive core only if it reaches >=80% player-season coverage in each fantasy position where absence is not itself the event. Injury-report nonappearance is treated as “not listed on the report,” not source missingness.

A descriptive source signal is called materially separating only if absolute univariate AUROC is >=0.60 with at least 30 TRUE-DEVELOPMENTAL and 30 PERSISTENT-DISAPPEARANCE observations. The report must also show effect direction and coverage so AUROC cannot conceal missingness or era concentration.

A provisional evidence-quality gate is satisfied only if: (a) at least two richer source families are broad; (b) >=70% of missing target rows receive a defensible factual status context rather than UNKNOWN; and (c) at least two independent factual source features meet the descriptive-separation standard. Passing this gate is necessary but not sufficient for E1: provenance/licensing, era bias, chronology, and governance remain separate requirements.

## Evidence eras
- Weekly roster/depth history is audited broadly from documented source inception, but the common rich descriptive core begins in 2012 because snap counts begin in 2012.
- Injury reports are available from 2009.
- The primary descriptive panel uses source seasons 2012–2023 so next-season context/outcomes are complete through 2024.
- 2024 evidence is reconstructed for coverage but is not used as a source-season discrimination row requiring 2025 outcome completeness.

## Licensing / governance standard
Repository or package license labels are recorded, but upstream-data terms are audited separately. Legal uncertainty is never converted into permission. A source can be judged suitable for research reconstruction while still requiring counsel/terms review before commercial production ingestion or raw redistribution.

## Decision
Conclude exactly E1/E2/E3/E4/E5 under the management packet. If E1 only, freeze an evidence contract for a *future* separately authorized Forecast study. Do not run that study here.
