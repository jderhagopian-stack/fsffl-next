# FSFFL NEXT — Management handoff | 2026-10-11

**Status: PROVISIONAL handoff updated after Work's bounded Career #405 tranche; overall Career Coverage remains incomplete.**
**Authority:** This is a point-in-time orientation, not a replacement for current `main`, accepted governance, the actual live PR state, or Work's later implementation report. Incoming Management must check those sources first. No merge, deployment, model promotion, or spending approval is implied.

## Mission and immediate sequencing

FSFFL NEXT is a dynasty/superflex fantasy-football decision-intelligence product. Our goal is to move from a technically sophisticated private beta to a fast, understandable, trustworthy and commercially viable owner experience.

**Management's accepted immediate sequence: Career Coverage #405 → Explore useful opportunity discovery → Trade Center decision quality.**

- Finish accepted existing-model-first, point-in-time player coverage. The frozen 335 players are a regression/reference cohort, not a production identity ceiling.
- Then make Explore produce realistic, diverse, actionable acquisition/waiver opportunities using cheap screening before targeted deep analysis.
- Then make Trade Center explain specific bilateral trades with roster/lineup, picks, team strategy, long-term Intrinsic and Simulation consequences.
- Keep owner intelligence, historical grading, What-If, storytelling and publications in the later product roadmap.
- One primary implementation lane and at most one narrowly scoped enabling lane. Each product milestone must pass a useful real iPhone/Safari owner journey and measure latency, memory and cost.

## Repo checkpoint — verified 2026-10-11

Repository: `jderhagopian-stack/fsffl-next`.
At handoff preparation, `main` HEAD was `df62354f3a40e4b30275645db0171bf518ed8a5b` (October 10); incoming Management must recheck.

**Open draft implementation PRs:**
- [#446](https://github.com/jderhagopian-stack/fsffl-next/pull/446): exact-State roster coverage accounting and player-specific missing-authority failures. It **does not** create missing Career estimates.
- [#447](https://github.com/jderhagopian-stack/fsffl-next/pull/447): sparse player prior. Research/optional fallback only; **not approved production P0 authority**.
- [#448](https://github.com/jderhagopian-stack/fsffl-next/pull/448): unchanged P0 scorer can process dynamic candidates with governed complete feature packets; synthetic mechanical proof, not general live evidence availability.
- [#449](https://github.com/jderhagopian-stack/fsffl-next/pull/449): real point-in-time candidate evidence integration for a bounded set, still reliant on existing provider ROS projections. Not proof of universal, independent or full Career coverage.

**Open draft research documentation PRs:**
- [#450](https://github.com/jderhagopian-stack/fsffl-next/pull/450) and [#451](https://github.com/jderhagopian-stack/fsffl-next/pull/451) were closed unmerged after their documentation was reconciled into #452.
- [#452](https://github.com/jderhagopian-stack/fsffl-next/pull/452) remains the current documentation draft for Experiments 1–2 (accepted research evidence; REVISE) and updated Career continuity. No merge is implied.

**Other relevant status:**
- [#445](https://github.com/jderhagopian-stack/fsffl-next/pull/445) bounded pending intelligence jobs was merged to main; current operations said **not deployed** at the last recorded checkpoint. Confirm live deploy separately.
- [#442](https://github.com/jderhagopian-stack/fsffl-next/pull/442) provider acquisition instrumentation merged and deployed, but natural request/byte evidence was not yet demonstrated at its acceptance checkpoint.
- [#443](https://github.com/jderhagopian-stack/fsffl-next/pull/443) storage write-safety prototype remains nonproduction / NO-GO. No migration authorized.
- Supabase Pro upgrade was independently recorded in canonical operations; previous Free-tier 512 MiB cap is not the operative plan-level gate. Cost, capacity and growth remain measurable concerns, not an automatic infrastructure workstream.

## Career Coverage #405 — immediate implementation instructions

The current Work implementation is expected to continue from latest main and the actual draft PR checkpoint, **without restarting research or duplicating completed work**.

Accepted scope:
1. Every exact-State rostered QB/RB/WR/TE (starter, bench, IR, taxi) must have a governed Career-forward estimate or a visible player-specific authority failure; #370 completeness must fail closed on missing required players.
2. Extend real point-in-time player evidence and unchanged accepted Forecast/P0 Y1–Y3, Y4–Y7, Y8+ tail, Career aggregation, and Shapley/value authority beyond the 335 reference players.
3. Preserve exact 335 parity, identity, scoring coordinate, source provenance/rights, State/publication fences, PIT, last-good restore, replay, uncertainty, and no fabricated missing observations.
4. Expand to a governed fantasy-relevant waiver/free-agent decision universe and bounded on-demand deep candidates. Market is a separate value coordinate, not a numeric Career Intrinsic input.
5. Reuse fitted model/training and global/provider evidence at the widest safe semantic scope; recompute only materially changed subjects/downstream league-dependent outputs; bound pending jobs; measure end-to-end latency/RSS and owner-visible coverage.
6. Do not treat a mandatory external projection dependency as solved independent forecasting. Do not use #447 sparse prior as production authority without separate approval.
7. Keep implementation isolated and reviewable; proportionate tests and actual iPhone/Safari validation before Management merge/deploy decision.

**Work checkpoint received — 2026-10-11:** Work completed the bounded materialization tranche in draft [PR #454](https://github.com/jderhagopian-stack/fsffl-next/pull/454), head `5b4b264816c3bf23221b011e59673c70bc2950c5`, based on `df62354f3a40e4b30275645db0171bf518ed8a5b`. On saved State `e431b5cb9e340e0f9a93e4433cafe51974fc8b86d6c56b1804e3e506013cd670`, it covers 2 of 27 out-of-reference rostered players with partial Y4–Y7/Y8+ authorities; 25 remain explicit unavailable statuses and there are 0 complete out-of-reference Career estimates. Waiver/free-agent and on-demand materialization remains 0. The bounded batch took 16.772 seconds and peaked at 469,260 KiB (~458 MiB), exceeding the existing ~410 MiB budget. Fourteen focused tests, compile/diff checks and focused CI run 5002 passed; stable full suite was skipped because the PR is draft. PR #454 remains unmerged and nonproduction. The accepted Y1–Y3 model/contract and established provider-rights handling remain settled. This is partial implementation evidence, not completion of #405.

## Independent Forecast / Intrinsic research — preserve, do not let displace product

North star: develop an independent, history-first in-house football forecasting and dynasty valuation capability, including rookies, backups, injured/developmental players and sparse histories, with opportunity, age, experience, career survival, uncertainty and historical PIT integrity. Third-party projections are optional evidence, not a mandatory permanent foundation.

Two **distinct research tracks**:
- Independent Year 1 forecasting (next-season).
- Independent history-first multi-year dynasty/career forecasting, **not blocked by Year 1 perfection**.

Recovered historical panel: 15,492 QB/RB/WR/TE player-season rows, 3,770 players, 1999–2025; 14,876 season-end origins, 11,106 observed next-season outcomes. Season-end chronology verified; exact historical calendar-date PIT not proven. Research/commercial source rights unresolved.

Experiments 1 and 2 used rolling held-out origins 2014–2024, 6,548 held-out origins, 4,862 explicit target rows and **1,686 missing next-season target rows (25.7%)**, never zero-imputed.

| Measure | Persistence | Experiment 1 | Experiment 2 |
|---|---:|---:|---:|
| Pooled observed-target MAE | 37.11 | 35.61 | 36.01 |
| Pooled observed-target RMSE | 56.22 | 50.76 | 51.17 |
| Nominal 80% interval coverage | — | 76.7% | 82.5% |
| One-season-history MAE | 31.52 | 33.34 | 34.52 |

Experiment 1 demonstrates modest independent signal but poor sparse-history/QB performance and undercoverage. Experiment 2's calibration improves pooled interval coverage but worsens point accuracy, overcovers WR/TE, undercovers QB, and worsens one-season-history results. Propensity weighting is a conditional-MAR sensitivity, not recovery of missing target outcomes. Neither establishes rookie coverage, exact calendar-date PIT, provider/P0 head-to-head or commercial-use permission.

**Management decision: ACCEPT as research evidence / model REVISE; no production promotion.** Do not automatically launch Experiment 3 or another broad recovery/audit. A future Year 1 experiment needs approved evidence distinguishing no participation/retirement/true zero from missing source coverage, or must explicitly target observed-returning-player outcomes. Preserve a separately bounded history-first dynasty experiment for when research capacity is available.

Detailed evidence: draft #452 `docs/research/INDEPENDENT_YEAR1_EXPERIMENTS_20261011.md`; draft #451 dedicated research workstream. Reproducibility reports/packages in ChatGPT Library. Avoid putting licensed/raw historical assets into public GitHub.

## Accepted architecture and safeguards

Preserve Data → point-in-time State → Forecast → Value → Decision → Search/Optimization → Presentation; accepted Simulation 2.0, immutable publication, tenant isolation, replay, last-good recovery and truthful readiness. No architecture rewrite. Design for eventual 100,000 leagues by safely sharing provider/model/scoring-cohort work, while validating smaller actual multi-league and 100/1,000 league gates before infrastructure expansion. No silent purchases, migration, licensed commercialization or model changes.

## Incoming Management — first actions

1. Read `AGENTS.md`, `docs/operations/CURRENT_OPERATIONS.md`, `docs/operations/MANAGEMENT_CONTINUITY.md`, `docs/operations/PRODUCT_ROADMAP.md`, `docs/FSFFL_NEXT_PRODUCT_PRIORITIES.md`, and `docs/operations/workstreams/CAREER_COVERAGE_EXTENSION.md`.
2. Check live GitHub `main`, open/merged PRs #446–#452, #445 deployment status and Work's exact implementation checkpoint. Treat this document as a dated snapshot.
3. Do **not** start a second Career worker, repeat historical recovery, restart independent Year 1 modeling, or begin a new architecture review.
4. Keep primary attention on Career #405 acceptance and Work's PR. Decide whether to approve merge/deploy only after exact evidence, parity, player coverage, rights/PIT, performance and real Safari acceptance are available.
5. Reconcile #450–#452 documentation without overwriting newer research evidence. Continue product order: Career → Explore → Trade.
6. Report to Management in concise plain English: what shipped/what is merely drafted, user-visible result, measured latency/cost, blocker, next approval.

## Next Management action

Continue the existing #405 implementation lane against the measured gaps: provide governed candidate packets and produce either a complete Career estimate or a reasoned player-specific failure for every exact-State rostered QB/RB/WR/TE; bring the materializer below the existing memory budget as a delivery constraint; then deliver governed waiver/free-agent and on-demand coverage. Preserve accepted model, Shapley, rights, #370, State/publication, PIT and last-good authorities. PR #454 remains draft; no merge, deployment, production-model change or infrastructure spend is authorized. When the Work implementation changes, incorporate its exact coverage counts, tests, memory, parity, and any Safari evidence into this record.

## Handoff authorization

This document is a **documentation-only continuity artifact** for transfer between Management chats. It authorizes no production action. The new Management chat should take over immediately, with Work continuing independently and reporting its final checkpoint later.
