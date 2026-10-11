# FSFFL NEXT — Independent Forecasting Architecture & Research Assessment

**Date:** 2026-10-11  
**Status:** MANAGEMENT GATE — FORECASTING RESEARCH  
**Base:** `main` at `df62354f3a40e4b30275645db0171bf518ed8a5b`  
**Scope:** Evidence review and design only. No fitting, production changes, authority promotion, merge, deployment, or infrastructure purchase.

## Executive assessment

FSFFL has meaningful independent historical research and career components, but accepted production does not yet constitute a projection-independent forecasting system. Accepted P0 uses a governed Year 1 source forecast and then combines its level/state and percentiles with historical production, coverage, position, age, experience, role/opportunity where available, and QB career evidence. The frozen 335 is a parity benchmark, not a production player universe. Its recovered thresholds and exact outputs must stay intact.

Current-season forecasting and dynasty forecasting are separate problems. The current P0 contract is not an independent Year 1 generator. Accepted Y2/Y3 and career machinery also use Year 1–Y3 as a starting coordinate or feature set. Thus neither is yet independent end to end.

The A2/Burr study documents about **+0.8969 pooled CRPS improvement versus production over 10,894 historical rows**, with point MAE approximately flat. This supports further use of in-house distributional evidence; it does not establish an independent Year 1 model. QB career-state evidence is more directly promising: chronological 2017–2022 evaluation won 6/6 folds, improving QB role calibration and Y2/Y3 error, but conditional production remains anchored to the authoritative Year 1 mean.

**Recommendation:** preserve production and PR #449; get approval for two bounded research protocols—independent Year 1 and history-first future-season/career forecasting—then evaluate them separately. No model fitting or broad implementation is authorized by this assessment.

## 1. Previous in-house forecasting attempts

| Work | Demonstrated evidence | Limits and disposition |
|---|---|---|
| **Accepted P0 / original 335** | Recovered source-state thresholds reproduce all 335 classifications. Features include Year 1 source level/state/percentiles, prior production and coverage, position, age, experience, and optional role/opportunity and QB-history evidence. | It scores future states; it does not generate independent Year 1. The feature effect/ablation of Y1 versus other features was not established in the reviewed records. Preserve coefficients, thresholds and exact benchmark. |
| **Accepted I1 / 3-Year Intrinsic** | Governed position-specific Y2/Y3 policies include role/career-state, bounded transitions or conservative carry-forward. QB integration has chronological validation (below). | Y1 is the base forecast and remains a conditional production anchor. Not projection-independent for players lacking provider Y1. |
| **A2 + Burr XII / direct-Gamma** | Frozen challenger: about **+0.8969 CRPS** pooled improvement vs P0/D0–D1 over **10,894 rows**, all positions/origins; point MAE approximately flat. Burr XII for QB uncertainty, direct-Gamma for RB/WR/TE. | Y2/Y3 distribution challenger, not Y1 generator; remained research/shadow. Earlier calibration variant failed a nominal-band coverage gate (4.2% vs 25%); broader calibration, packaging/replay and coverage gates remained. This is not evidence the model family failed outright or was production-ready. |
| **QB career-state** | Meaningful-starter target: ≥200 pass attempts. Chronological 2017–2022 deployment-shaped comparison won 6/6 folds. All-QB Y2 MAE 64.701→57.162 (11.7%); Y3 74.221→62.019 (16.4%). Y2/Y3 Brier 0.1203/0.1384 vs baseline 0.2410/0.2285. In 9,430 OOT Intrinsic rows, MAE 20.307→19.981; non-QB outputs unchanged. | Strong QB starter-role probability from age, experience, draft percentile, participation/opportunity, role history and production percentile. Conditional production still uses Y1 mean × role probability. QB-only, versioned/season-scoped, not a universal Y1 or career model. |
| **Career / Y4–Y8 research** | Multiple chronological studies measure history, age/experience, role/trajectory, survival and annual tails. Six-family comparison: two_part_state won RMSE/survival in 14/20 cells; direct_ridge won MAE in 17/20 but lost RMSE and tail RMSE in 20/20. A frozen richer 75/25 specialist/shared challenger failed untouched QB-Y8 safety (RMSE 100.44 vs 77.84; ratio 1.290 vs 1.15 gate). Later 11,940 rolling origins supported soft shrinkage generally, but exact support only QB Y4, WR Y4, QB Y6; Y8 insufficient. | These studies used governed Y1–Y3 features. Their results establish genuine but horizon-limited signal and material model/uncertainty limits; they do not prove a projection-independent Y1–Y3 dynasty pipeline. Research conclusions from distinct studies should not be combined as one production authority. |
| **Injury / availability** | Historical evidence includes 4,793 injury episodes; separate remaining-season availability and return-time work exists. | Availability is not healthy conditional production, future career survival, post-return role, or a complete forecast. |
| **Live acquisition and PR #449** | Existing Sleeper completed-season/weekly stats and CBS/Razzball ROS acquisition, canonical mapping, normalization, scoring and PIT integration are useful seams. PR #449’s successful work is to remain preserved. | Projections are optional evidence/benchmarks under this objective. Provider absence does not prove football evidence is absent. Keep #449 separate, draft and unmerged. |

### What is known versus still unproven

**Demonstrated:** Y1 is a required input/base in accepted P0/I1/career paths; QB conditional production is Y1-anchored; Y4+ research consumes Y1–Y3 feature coordinates; some challenger variants failed preregistered calibration or holdout safety gates; long-horizon support varies by position/horizon.

**Not demonstrated:** that external Y1 projections dominate P0 numerically (no accepted ablation/attribution was found); that an independent Y1 model cannot beat history baselines; that A2/Burr has no value; that one failed cell invalidates other career signal; or that rookies, injured players and backups are unforecastable from approved evidence. Test these questions; do not convert missing research into assumed failure.

## 2. Reusable assets and coverage limits

| Asset | Reuse | Limit |
|---|---|---|
| Historical player-season production, canonical IDs, age/experience | Lags, rates, trajectory and chronological target construction. | Confirm point-in-time availability, completeness, identity and scoring semantics at every origin. |
| Weekly stats, participation, snaps, role/opportunity | In-season actuals and role evidence. | Era/position coverage varies; retain provenance and missingness meaning. |
| Injury episodes/statuses | Availability and time-to-return targets. | Not healthy production, post-return role or long-term career risk without separate evidence. |
| Draft/pedigree/prospect features | Potential entrant cold-start evidence; prior rich Y4+ research used pedigree families. | No accepted all-position prospect-to-fantasy runtime was identified; verify timestamps, rights and coverage. |
| QB career-state artifact | Validated QB role/survival probability. | QB-only and conditional points remain Y1-based. |
| P0, A2/Burr, transition and tail models | Reuse transforms, state decomposition, uncertainty and scoring contracts as research candidates. | Preserve P0 authority; career/tail artifacts currently depend on Y1–Y3 and frozen 335 feature boards. |
| League scoring, canonical identity, ROS acquisition | Scoring translation and source-neutral candidate/runtime seams. | Separate football forecast authority from deterministic league scoring and source provenance. |

Cohort implications:
- **Established players:** strongest historical production and role evidence.
- **Injured players:** availability can be modeled separately; conditional healthy production/post-return role remain distinct gaps.
- **Backups/deep reserves:** roster, participation, snaps and opportunity may inform role transitions; never infer zero or healthy from missingness.
- **Rookies/developmental entrants:** require time-stamped, rights-cleared draft/prospect, age-at-entry, team and role evidence plus calibrated entrant uncertainty. No accepted all-position independent model was located.
- **No-provider-projection players:** may still have useful historical/role evidence. Missing provider rows are not evidence of missing football inputs.

## 3. Independent Year 1 architecture

Treat Year 1 as a distinct current-season target with two evaluation modes:

1. **In-season:** observed scoring through a cutoff plus remaining-season production. Use only completed weekly actuals, participation, role/opportunity, dated team status and injury/availability evidence available before that cutoff.
2. **Preseason:** full-season expectation before NFL outcomes. Use historical production/efficiency, age/experience, prior role, dated current opportunity/team/injury evidence and a separately evaluated rookie/prospect path.

At either origin, record canonical identity, source timestamp, coverage/completeness, rights, and scoring provenance. External ROS projections may later be optional benchmark/covariate evidence; they must not be mandatory fields or labels. Estimate football production/stat distributions first, then apply governed league scoring. Historical replays are reproducible only when the feature and its as-of timestamp were retained; otherwise mark evidence unavailable and never backfill later facts.

Before proposing a Year 1 model, complete a source/feature/rights/identity/availability matrix by season, position and evidence cohort; freeze target/cutoffs; define a history-only baseline; and demonstrate chronological coverage. This directive authorizes design and recommendation, not fitting.

## 4. History-first dynasty architecture

Model each future year as (a) probability of remaining present/relevant/available and transitioning among role/opportunity states, and (b) a conditional production distribution. Use completed production/opportunity history, age, experience, cumulative exposure where historically measured, career-stage trajectory/volatility, role continuity, injury/availability, and prospect/draft evidence for entrants. Forecast future seasons directly or through empirically validated state transitions; do not initialize every horizon from external Year 1.

Keep within-player uncertainty, model-authority disagreement, sparse-evidence uncertainty and scoring translation separate. Existing Y4–Y7 and Y8+ machinery can inform survival/conditional-production separation, tails and uncertainty; it cannot be treated as a projection-free model because its features include Y1–Y3 and its current board is cohort-frozen. Any independent reuse needs a distinct feature contract and historical validation.

## 5. Validation design before fitting

Use rolling-origin chronological season folds, with all selection/tuning contained within each origin’s past. Group player-seasons by time; strict as-of joins; no future injury, status, role, transaction or provider revision; no random row splits. Label already-inspected seasons as repeated OOT validation, not untouched holdout.

| Track | Core measures | Comparators |
|---|---|---|
| Independent Y1 | MAE, RMSE, bias, rank/Spearman; CRPS/pinball, interval coverage/width if distributions are produced. Score underlying production under official league rules. | Last-season/persistence and position-season history baselines; P0/current provider route on comparable rows; CBS/Razzball/FFToday only where permitted and sourced. |
| Dynasty trajectory | Annual point/rank errors by horizon; relevance/role Brier/log loss and transition calibration; distribution CRPS, tail error and uncertainty coverage. | History persistence/carry-forward, accepted P0-fed Y2/Y3, accepted long-horizon research baselines, provider-fed outputs only on common origins. |
| Product impact | Player-season trajectories, ranking/value reversals and uncertainty on identical scoring/identity coordinates. | Existing 3-Year and Career Intrinsic outputs, without using Value to tune Forecast. |

Report QB/RB/WR/TE and established starters, backups/deep reserves, injured/limited, rookies/first-year, developmental, sparse history and no-provider-projection groups separately with sample count and feature availability. Quantify paired difference uncertainty by player/season blocks. Assess central accuracy and probabilistic quality separately; no incumbent privilege or arbitrary replacement margin. Source rights, identity ambiguity and unsupported historical features fail closed.

Before authority review require a frozen manifest, reproducible OOT forecasts, common-row P0 and simple-baseline comparisons, calibrated uncertainty, subgroup safety, era/missingness sensitivity, rights review and independent reproduction. Then obtain a separate Management decision.

## 6. Smallest credible sequence and approval request

1. Preserve P0 thresholds/335 parity, PR #449 and all existing artifacts; create an evidence ledger of target, inputs, origin, validation, rights and authority. Avoid rerunning exact studies.
2. Management approves a preregistered independent Y1 protocol: feature/source availability and rights, PIT reconstruction, separate preseason/in-season targets, baselines, metrics and subgroup gates.
3. After approval, run bounded Y1 feasibility research; do not refit production P0.
4. Separately approve and test history-first dynasty targets and PIT features against current P0-fed models on common origins.
5. Evaluate sparse/rookie/injured cohorts; report calibrated uncertainty or evidence failure rather than arbitrary zeros, generic averages or borrowed provider values.
6. Only after both research gates, propose a source-neutral Forecast contract and separately reviewed integration PR. External projections remain optional evidence.

**Management decisions requested:** approve/revise (a) independent Year 1 study protocol, (b) separate history-first dynasty study, (c) optional rights-scoped external benchmarks, and (d) explicit low-confidence/unavailable historical outcomes where retained evidence cannot reproduce the origin. No challenger training or production implementation begins in this stage.

## Source records

`docs/operations/MANAGEMENT_CONTINUITY.md`; `docs/operations/workstreams/RESEARCH.md`; `docs/research/QB_CAREER_STATE_INTRINSIC_V1_READINESS.md`; `docs/research/INTRINSIC_VALUE_V1_PRODUCTION_DECISION.md`; `artifacts/implementation/forecast_intrinsic_i1_validation_protocol.md`; `artifacts/implementation/final_forecast_architecture_reconciliation_20260919/ARCHITECTURE_RECONCILIATION_STOP.md`; `artifacts/implementation/forecast_source_coordinate_20260919/FINAL_CLOSURE_AND_CREDIBILITY_OUTCOME.md`; `artifacts/implementation/preseason_forecast_resilience_reconciliation.md`; `artifacts/research/intrinsic_comprehensive_y4_y8_20260926/MANAGEMENT_HANDOFF.md`; `artifacts/research/intrinsic_y4plus_model_family_20260926/FINAL_CLOSEOUT.md`; `artifacts/research/intrinsic_cell_routing_y4_y8_20260926/MANAGEMENT_HANDOFF.md`; and PR #449 integration evidence.
