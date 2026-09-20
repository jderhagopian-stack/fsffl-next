# FSFFL NEXT — Final Forecast Architecture Reconciliation Stop

Date: 2026-09-19  
Classification: **STOP - ARCHITECTURE RECONCILIATION FAILURE**

## Executive result

The complete selected Forecast architecture is **not** what PR #147 currently executes for Years 2 and 3.

The authoritative research evidence selects:
- Year 1: preserved FFToday + Razzball preseason raw-stat baseline, scored under league rules;
- Years 2/3: fixed routed Forecast (**QB A2+C+D; RB/WR/TE A2+D**) plus frozen **M1a** continuous within-state magnitude plus the frozen **two-prior-season consistency** adjustment;
- then the promoted player-specific scoring translation;
- then calendar composition and Intrinsic/Shapley.

PR #147 instead still produces future states/points with the embedded legacy `FrozenI1Artifact` pair `_H12` / `_H3`. The recently promoted player-specific scoring layer translates those legacy outputs into league scoring units; it does not replace the upstream legacy I1 producer with the selected routed Forecast.

That is a direct authoritative-layer bypass/replacement. The management directive therefore requires a stop before final-board materialization or merge-readiness.

## Complete selected stack and current status

| Layer | Repository-selected role | Status in PR #147 |
| --- | --- | --- |
| Frozen preseason source evidence | FFToday + Razzball, immutable raw-stat ensemble | Authoritative + wired |
| Year-1 league scoring | Directly score frozen raw stats under connected league rules | Authoritative + wired |
| Standard compatibility coordinate | Direct-score same raw stats under frozen non-PPR rules for future-model compatibility | Authoritative + wired |
| A2 | Exact-age persistence form with position-specific continuous age/hinges | Authoritative, not current future producer |
| C | Prior age/state residual memory; selected route retains C for QB | Authoritative, not current future producer |
| D | Within-current-state percentile/tail calibration for positive-state transitions | Authoritative, not current future producer |
| Routing | QB A2+C+D; RB/WR/TE A2+D | Authoritative, not wired as Y2/Y3 runtime |
| D0/D1 production | D0 conditional-active level; D1 positive-state-conditioned means | Authoritative, not wired as Y2/Y3 runtime |
| M1a | Continuous within-state magnitude residual-z adjustment; probabilities unchanged | Authoritative, not wired |
| Two-prior consistency | Prior-two residual mean/gap/coverage adjustment; probabilities unchanged | Authoritative, not wired |
| Player-specific league scoring | Player league-Y1 / standard-Y1 ratio; point-unit translation only | Authoritative + wired, but consumes wrong upstream Y2/Y3 producer |
| Calendar | Y1 + direct Y2 + direct Y3; diagnostic h1 excluded | Structurally wired |
| Intrinsic/Shapley | Frozen downstream Shapley/discount/lineup scarcity | Structurally wired, but consumes wrong Y2/Y3 authority |

Superseded/rejected for this selected Forecast include M1b, M2, M3a, M3b, role/security, third-prior-season, hard repeated-elite tier, new interactions, named-player overrides, P1 magnitude anchor, and P2 relative-retention target.

## What P0 is — and is not

Repository evidence uses **P0** as the retained control/deployment package for the frozen Outcome-B future conditional-production architecture and selected route. The corrected preseason gate could replay that package over the preserved standard Year-1 coordinate without fitting.

P0 is **not the whole Forecast**. It does not own the two frozen provider inputs, direct Year-1 league scoring, the downstream player-specific league-scoring translation, calendar composition, or Intrinsic/Shapley. The selected full Forecast also includes the routed state/probability machinery and the later frozen M1a + two-prior production decisions.

Most importantly, the corrected P0 gate explicitly recorded that it did **not** modify PR #147 runtime Forecast authority. A diagnostic P0 replay is not proof that the PR runtime consumes the selected future model.

## Exact runtime discrepancy

Current `PrivateBetaShapleyContractLoader`:
1. loads `frozen_i1_h12.json` and `frozen_i1_h3.json` into `_H12` / `_H3`;
2. maps completed-source I1 facts;
3. calls `compose_live_intrinsic_calendar(... h1_h2_predictor=_H12, h3_predictor=_H3 ...)`;
4. only afterward applies the promoted player-specific scoring translator.

The activation builder itself fits `IntegratedI1Model` and serializes `FrozenI1Artifact`. It is not the selected A2+C+D/A2+D routed production-resolution package.

The earlier durable reconciliation artifact already identified this exact problem at the durability gate. Comparing that stop-era PR head to the current head shows later work added corrected-P0 diagnostics and player-specific scoring, but did not add/wire the selected routed Forecast as the runtime Y2/Y3 producer.

## Frozen preseason lineage — PASS

- production baseline record 145;
- source artifact 94;
- frozen sources: FFToday + Razzball;
- 1,675 raw observations / 335 players;
- raw-array SHA-256 `4dd1fa70b9b4f886ad103a2f5b6f45f7c4f123a571f84b7a4400b0004271639d`;
- connected-league Year-1 board SHA-256 `6bded35221a501471df60de8c05a6e691428552f23abb3f0cf799218fd71bfae`;
- standard/non-PPR board SHA-256 `dfe817909dc42782ef4f1249692a9ad9139b5fa25311549ae741970c4ef9efe9`.

Year 1 is therefore not the blocker.

## Why the final Y1/Y2/Y3 board was not materialized

The directive permits final 335-player materialization **only after architecture reconciliation passes**. It did not pass.

A prior 335-player / 670-future-row corrected-P0 diagnostic exists and passed its bounded credibility gate, but its own manifest says PR #147 runtime Forecast authority was unchanged. Treating that diagnostic as the final wired Forecast board would violate the directive and hide the very architecture discrepancy this review was asked to detect.

Accordingly:
- no new “final” Y1/Y2/Y3 board was fabricated;
- no final position summary/outlier list was produced;
- no final cross-horizon or Shapley propagation verdict was asserted.

## Workflow terminal state

- CI #2103: **SUCCESS**, 1,243 passed / 2 warnings.
- Activation-artifact workflow #102: **SUCCESS**. Artifact/schema verification passed, current fact rows = 756, frozen research-coordinate parity passed, and `model_changes=false`.
- Private-beta Intrinsic live diagnostics #83: **FAILURE**, but its focused tests passed (35 passed) and frozen-coordinate credibility board passed. The failing step was current live-provider acquisition: only Razzball succeeded; FFToday returned 403, CBS was rejected as non-full-season, and NFL Fantasy returned no projection content.

The live-provider failure is analytically separate from the frozen preseason architecture. The activation workflow being green likewise does not resolve the wrong Y2/Y3 runtime authority.

## Final classification

**STOP - ARCHITECTURE RECONCILIATION FAILURE**

A previously selected authoritative Forecast layer is bypassed/replaced in the current PR: the selected routed Forecast + M1a + two-prior future architecture is not the runtime Years 2/3 producer; legacy embedded I1 remains the producer.

No merge, deployment, main modification, refit, retune, model-selection reopening, scoring-coverage broadening, or final-board substitution was performed.

**Return to management at this exact boundary.**
