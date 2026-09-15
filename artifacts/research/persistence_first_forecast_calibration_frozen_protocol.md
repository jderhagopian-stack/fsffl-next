# FSFFL NEXT — Persistence-First Forecast Calibration Frozen Protocol

RESEARCH ONLY. DO NOT MERGE OR PROMOTE.

This protocol is frozen before the persistence-first challengers are executed. The Intrinsic Constitution, B4 holding governance, frozen Shapley/W, 2048-permutation Shapley precision budget, Value authority, anticipated-production means, and production authority are unchanged.

## Authoritative starting state

- production `main`: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #139: draft/open/unmerged, `ff534c52e8e9694ebdae7f48df209ada0cc3f555`
- PR #140: draft/open/unmerged, `002afcd5b6d25ade12317a563330658a77791526`
- PR #141: draft/open/unmerged, `5a37d831ed759a76d26742e5295e863d150dbaf0`
- PR #142: draft/open/unmerged, `724ae9a6c6e9585702ffaf5808aaeb7e1af1bd3b`
- PR #143: draft/open/unmerged, `6401d7b3d6fcdae3f6bdea6c3b0348881a2473e7`
- PR #144: draft/open/unmerged, `5c2e5b847a79ce5f24fac2c47d1d1334264faa12`

## Phase 0 parity gates

The run must reproduce, without retuning, the retained C0-C3 Forecast summaries from PR #142 and the event-time evidence summary from PR #144. Material parity failure stops the study.

Frozen retained controls include:
- C0 low-end state Brier `0.17558645736306655`; predicted OUT `0.006915791295527824`; realized production-panel OUT `0.5940140845070423`; true-developmental recall `0.9939393939393939`; low-end breakout false-negative `0.0031690140845070424`; low-end false-positive developmental `0.7105633802816902`.
- C1 low-end state Brier `0.10702400043132294`; predicted OUT `0.45028575400143417`.
- C2 low-end state Brier `0.10642416282705278`; true-developmental recall `0.5515151515151515`; low-end breakout false-negative `0.15176056338028168`.
- C3 low-end state Brier `0.1081123053832698`; true-developmental recall `0.5636363636363636`; low-end breakout false-negative `0.14894366197183098`.
- event-time factual resolution: `74.05%` resolved / `25.95%` unresolved across 925 low-end missing rows; non-IR injury-limited share `4.42%` among later-return vs `0.40%` among persistent-disappearance cases; roster continuity strongest; `active_return_count` is the retained nonredundant transition signal.

## Canonical provider-neutral fact contract

Forecast logic may consume only canonical FSFFL facts. Provider-specific raw codes may be used only inside research adapters that map into this contract.

### Identity/context
- `position`: QB/RB/WR/TE.
- `age_years`, `age_band`: age at source-season decision point.
- `experience_years`: completed NFL experience at source point.
- `current_state`: governed scoring-normalized football state.
- `horizon`: 1 or 2 seasons.

### Production/role
- `current_fantasy_points`: source-season governed realized production.
- `opportunity_per_game`: governed position-appropriate opportunity per game when available.
- `role_band`: provider-neutral weak/established role band from governed opportunity data.

### Organizational attachment / churn
- `roster_continuity_share` (`active_share` in the research adapter): fraction of observed source-season roster-status records classified active.
- `released_share`: fraction classified released/free-agent family.
- `practice_squad_share` (`practice_share`).
- `reserve_share`.
- `last_status_active`, `last_status_attached`, `last_status_release`, `last_status_practice`, `last_status_reserve`.
- `status_transition_count`, `team_change_count`, `active_return_count`, `release_entry_count`, `practice_entry_count`, `reserve_entry_count`.
- `roster_evidence_coverage`: factual source-season roster-status evidence present.

### Availability / participation (M3 only)
- `injury_report_weeks`, `injury_limited_weeks`.
- `non_ir_injury_limited_weeks`, `non_ir_injury_flag`.
- `inactive_injury_limited_weeks`, `inactive_injury_flag`.
- `reserve_injury_limited_weeks`.
- `participation_weeks`, `stats_weeks`, `snap_play_weeks`.
- `availability_evidence_coverage`.

### Provenance/missing semantics
Every canonical field retains source family, source season/timestamp rule, coverage flag, and provider version in the research artifact. Missing injury evidence is not healthy; missing transaction evidence is not retained; missing roster evidence is not released.

## Factual persistence outcome semantics

The two-stage model changes the meaning of Forecast OUT from “no production row observed” to the authorized organizational-persistence question.

At horizon `h`, a retrospective persistence label is:
- `PERSIST=1` if a governed target-season production row exists, or if direct target-season football-state evidence establishes continued organizational attachment (active/inactive roster, practice squad, reserve/PUP/NFI, suspension/exempt, or another governed attached state).
- `PERSIST=0` only if direct target-season evidence establishes non-persistence (retired, terminal waived/released/free-agent state without later target-season reattachment).
- `UNRESOLVED` if neither condition is factually established. Unresolved rows are not relabeled as deaths and are excluded from Stage-1 fitting and primary factual persistence/state scoring; they remain in explicitly reported coverage/fallback diagnostics.

For primary multiclass factual scoring:
- non-persistent resolved rows are `OUT`;
- persistent rows with positive governed production use the existing depth/usable/starter/premium/elite state definition;
- persistent rows with no positive production are conservatively labeled `DEPTH` for the conditional football-state evaluation;
- unresolved rows are not forced into a state.

Future later-return/breakout/persistent-disappearance labels are evaluation-only and never predictors.

## Frozen comparison set

### M0 — current baseline
The unmodified C0 transition estimator / governed QB override from the retained research harness.

### M1 — prior best soft-disappearance control
C2 from PR #142, selected solely because it had the lowest retained low-end state Brier among the frozen C1-C3 controls. No retuning.

### M2 — persistence-first organizational challenger
Two stages:
1. Stage 1 estimates `P(PERSIST)` with a fixed L2-penalized logistic model (`C=1.0`, LBFGS, max_iter=2000, no class weights, deterministic feature order) using canonical identity/context, production/role, and organizational-attachment/churn facts.
2. Stage 2 takes the existing M0 football-state vector after the governed QB override, removes OUT, and renormalizes depth/usable/starter/premium/elite to sum to 1. No new conditional-state learner is fit.
3. Combine: `P(OUT)=1-P(PERSIST)` and `P(s)=P(PERSIST)*P_M0(s | positive state)`.

### M3 — persistence-first + richer availability challenger
Predeclared now because the completed event-time evidence audit independently established a distinct factual availability family before this model study. M3 is identical to M2 except Stage 1 may additionally consume the canonical availability/participation fields listed above. M3 is not created or changed in response to M2 results.

No other challenger is authorized.

## Frozen feature/fallback hierarchy

For each fold and horizon, Stage 1 fits only on strictly earlier source seasons with resolved factual persistence labels.

1. **Full evidence model**: used only when source-season roster evidence is present; M3 additionally requires availability-family coverage for its availability terms.
2. **Reduced model**: fixed provider-neutral identity/context + production/role fields; no roster/availability facts.
3. **Resolved empirical prior**: Beta(0.5,0.5)-smoothed persistence rate using, in order, `(position, age_band, current_state, horizon)`, `(position,current_state,horizon)`, `(position,horizon)`, requiring at least 30 resolved observations in a cell.
4. **Conservative broad fallback**: M0 survival probability. This fallback is reported, never hidden.

A logistic model is considered estimable only with at least 100 labeled rows and at least 20 examples in each class. Otherwise the next fallback is used. Continuous predictors are standardized using training-fold statistics only. Canonical categorical variables are one-hot encoded with a fixed vocabulary; no category discovered in the test fold changes the feature schema.

## Strict chronology

Predictors for source season `t` use only facts timestamped in/completed by `t`. Target-season organizational facts and target production are labels only. Training labels for fold `T` require source season `<T`; no source-season row from `T` or later is used to fit a model predicting `T`. Later return and later breakout never enter predictor construction.

All 18 retained historical fold seasons remain in the report. Pre-rich-evidence folds may invoke the declared fallback; they may not be silently removed. Primary factual-persistence scoring reports resolved-label coverage separately by fold/era/position.

## Frozen evaluation metrics

Report M0/M1/M2/M3 on:
- factual persistence Brier/log loss, mean predicted non-persistence vs observed non-persistence, and 5-bin calibration;
- factual multiclass state Brier/log loss;
- useful/starter/premium threshold Brier;
- legacy production-panel state metrics for continuity with prior work (clearly secondary to the factual-persistence semantics);
- true-developmental recall at the retained 0.50 useful-probability diagnostic threshold;
- breakout false-negative and false-positive developmental rates;
- later-return, non-IR injury, reserve/practice, and active-roster-no-production cohorts;
- QB/RB/WR/TE;
- young/prime/aging and governed experience bands;
- early 2012-2015 / middle 2016-2019 / recent 2020-2022 plus explicit pre-2012 fallback history;
- full/reduced/prior/broad-fallback prediction paths and unresolved target-label coverage.

## Frozen promotion guardrails

A candidate is promotable for management review only if all tests pass.

- **G1 low-end persistence calibration:** on resolved low-end factual labels, persistence Brier improves >=10% vs M0 and absolute mean non-persistence calibration error is no worse.
- **G2 multiclass state calibration:** resolved low-end factual state Brier improves >=5% vs M0; resolved low-end state log loss may not worsen >2%.
- **G3 true-developmental preservation:** recall decline <=3.0 percentage points vs M0.
- **G4 breakout false-negative:** increase <=3.0 percentage points vs M0.
- **G5 false-positive developmental:** relative reduction >=10% vs M0.
- **G6 position safety:** no position with >=30 resolved low-end rows may have factual state Brier degradation >5% vs M0.
- **G7 era safety:** no rich-evidence era with >=30 resolved low-end rows may have factual state Brier degradation >10% vs M0; pre-2012 fallback use must be explicit and cannot count as an improvement claim.
- **G8 temporary-absence safety:** among each sufficiently sized (n>=20) later-return / non-IR-injury / reserve-practice cohort, mean predicted persistence must be >=0.70 and the share with predicted persistence <0.50 must be <=20%; candidate must also be no worse than M1 on that cohort’s factual persistence Brier when factual labels exist.
- **G9 overall Forecast safety:** resolved overall factual state Brier may not worsen >2% vs M0, and legacy overall state Brier may not worsen >2% vs M0.
- **G10 PIT / authority / leakage:** mandatory static/runtime audit pass; no market/owner/trade/fantasy-roster predictors, no future-outcome predictors, no Value/Shapley feedback.
- **G11 source-agnostic semantics:** mandatory pass; model code consumes canonical names only; provider raw status codes remain confined to the adapter.

If both M2 and M3 pass all guardrails, choose the lower resolved low-end factual state Brier; if within 1% relative, prefer simpler M2. If neither passes, no candidate is selected.

## Anticipated-production means

Frozen. State-path results may diagnose the existing mean path but may not modify anticipated production means. Report whether state-path correction reduces low-end excess future rights and whether true-developmental conditional production remains underpredicted.

## Downstream Shapley gate

Shapley may not select Forecast. Run frozen 2048-permutation Shapley only if M2 or M3 independently passes all G1-G11. Otherwise downstream Shapley is not authorized.

## Decision mapping

- P1 only if a frozen candidate passes all G1-G11.
- P2 if two-stage persistence-first is directionally successful but one or more material guardrails fail.
- P3 if evidence coverage/semantics prevent defensible estimation despite the frozen fail-closed hierarchy.
- P4 if the two-stage architecture does not materially improve the problem.
- P5 only if authoritative prior findings fail reproduction after audit.

No post-result threshold changes, new features, new challenger, rescaling, Value repair, or named-player tuning are allowed.