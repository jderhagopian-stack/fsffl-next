# FSFFL NEXT — Live Forecast Time Coordinate & Horizon Research Protocol

Status: **RESEARCH ONLY — PRE-RESULTS FROZEN PROTOCOL**

Authority: management directive dated 2026-09-15. This branch must not modify, rebase, merge, or replace implementation PR #147, production `main`, the Intrinsic Constitution, B4, Shapley W, the 0.85 career discount, market coordinates, Team Utility, Decision/Search, or production authority.

## 1. Research question

At an evaluation date inside an active season, determine the smallest governed Forecast coordinate that can map expected competitive production to three real calendar seasons (evaluation year, +1, +2) without relabeling historical horizons, recursion, invented evidence, or downstream Value/Shapley tuning.

## 2. Frozen Forecast architecture

- Forecast architecture remains I1.
- Regularization remains global `C=0.25` with no developmental override.
- Same source features, rich/reduced evidence paths, state definitions, minimum-fit rules, monotonic ordered thresholds, persistence/state decomposition, and state-conditional production semantics as the selected I1 research.
- No market prices, dynasty rankings, fantasy ownership, trades, owner behavior, Team Utility, Shapley, or Value outcomes may enter Forecast selection.
- No live 2026 player outcomes may be used to fit, tune, select, or validate the candidate.

## 3. Time terms

- **Completed source season S:** last full factual football season used as the source record for completed-season I1.
- **Evaluation season E:** calendar season in which a live product request occurs.
- **Target calendar season T:** real season whose production is being forecast.
- **Model horizon h:** direct offset `T - S` for completed-season I1. `h=1` means S+1; `h=2` means S+2; candidate `h=3` means S+3.
- **Intrinsic display year:** calendar year shown to the user after Forecast authority is frozen; it must never redefine model horizon labels.

## 4. Phase-A authority map frozen before new results

1. Production already has a distinct governed live/current-season Forecast authority based on as-of-week actual production plus remaining projection evidence. It is not completed-season I1 and is not realized production alone.
2. Completed-season I1 directly maps `h=1 -> S+1` and `h=2 -> S+2`.
3. For a live 2026 evaluation with completed source S=2025, those I1 horizons target 2026 and 2027. They do not authorize 2028.
4. FSFFL has prospective durable projection-history infrastructure, but the production `fsffl.projection_snapshot` store contained **0 rows** at the pre-results audit. The table itself was introduced by the 2026-09-11 migration. Therefore no multi-season historical as-of-date projection archive exists in FSFFL today for honest in-season future-model training.

## 5. Candidate set and pre-results exclusions

### Candidate A — direct completed-season h=3

Authorized for testing. Train and evaluate a direct S -> S+3 I1 target. This is not recursion and must independently learn persistence/state probabilities and state-conditional production means from factual S+3 outcomes.

### Candidate B — genuine in-season PIT future Forecast

**Excluded before result inspection.** Infrastructure can store future live snapshots, but the historical projection archive required to reconstruct multiple past in-season as-of-date information sets does not currently exist. Backfilling later-observed projections would violate PIT governance. Candidate B may be revisited prospectively after sufficient snapshots accumulate or a separately licensed/verified historical archive is obtained.

### Candidate C — governed calendar-ownership hybrid

Authorized only as a semantic composition after Candidate A Forecast selection. It is not a new predictive model. If Candidate A validates, inspect whether the existing current-season Forecast owns calendar Year E while completed-source I1 owns later years. No current-season projection may be fed into I1 as completed facts.

## 6. Historical evaluation design

### Direct h=3 selection history

- Target evidence is factual through 2024.
- Rolling-origin selection folds use source seasons **2014–2020**, where h=3 targets 2017–2023.
- The **source-2021 -> target-2024** fold is untouched confirmation and may not be inspected until the h=3 selection decision is frozen.
- Earlier eligible history may be used for training subject to source/evidence contracts.

### Strict chronological fitting

For an evaluation source season `S_eval`, a training row at horizon h is eligible only when its factual target would already have been knowable before that evaluation source season: `source_season + h < S_eval` under the existing completed-season cutoff convention. No target outcome from S_eval or later may leak into training.

### Reference horizons

Run the same rolling protocol for h=1 and h=2 only as context for horizon degradation and uncertainty. They are not reopened for model-family selection.

## 7. Direct h=3 baseline and selection

The h=3 candidate will be compared against a pre-existing-style empirical direct transition prior built from the same PIT training rows (position / age-state / current-state backoff) with state-conditional production means. This baseline answers whether the fitted I1 features add useful signal beyond historical direct transition frequencies without introducing a new model family.

The candidate is selected on Forecast evidence only. No single weighted score will be created.

Required evidence:
- factual state Brier and state log loss;
- persistence Brier/log loss;
- useful/starter/premium Brier and discrimination where supported;
- anticipated-production MAE and bias;
- developmental recall and false optimism;
- temporary-absence/reserve safety;
- position, age/experience, era and fold stability;
- coverage/resolution and rich/reduced/fallback paths;
- calendar coherence;
- honest longer-horizon uncertainty.

A direct h=3 may be frozen as valid only if it shows a coherent, repeatable forecasting advantage over the empirical direct baseline, does not create material subgroup safety failures, and retains coherent performance on the untouched 2021 -> 2024 confirmation. Marginal aggregate improvement with unstable folds or material subgroup degradation is insufficient.

## 8. Uncertainty rule

Year-3 output must not imply the same certainty as shorter horizons merely because the API shape is the same. Report empirical error/calibration dispersion and horizon-specific uncertainty diagnostics. If a production confidence interval is eventually surfaced, it must be derived from validated horizon-specific residual evidence rather than an arbitrary multiplier.

## 9. Selection freeze and downstream test

1. Complete rolling h=3 selection evidence without reading the source-2021 confirmation.
2. Write a research selection-freeze artifact stating whether direct h=3 is accepted or rejected.
3. Only then run the untouched source-2021 -> target-2024 confirmation.
4. Freeze the final Forecast calendar coordinate before any Shapley/Intrinsic result is inspected.
5. Only after Forecast freeze, run the frozen 2,048-permutation Shapley diagnostic and locked 10-point Intrinsic Constitution. These downstream outputs may identify a contradiction but may not choose or retune Forecast.

## 10. Possible calendar composition if h=3 validates

During an active evaluation season E with completed source S=E-1, the candidate semantic bridge to test is:

- Intrinsic calendar Year E: existing authoritative live/current-season Forecast.
- Intrinsic calendar Year E+1: completed-source direct I1 `h=2` (S+2 = E+1).
- Intrinsic calendar Year E+2: completed-source direct I1 `h=3` (S+3 = E+2).

Completed-source I1 `h=1` remains a same-calendar-year diagnostic/reference for E; it is not relabeled as E+1 and is not double-counted.

If h=3 does not validate, no 2028 value will be manufactured. The fallback is an explicitly shorter live horizon pending better evidence.

## 11. Stop rules

- Stop Candidate A if direct h=3 lacks coherent predictive skill or adequate coverage.
- Do not respond by inventing recursion, extrapolating h=2 coefficients, relabeling horizons, or reopening Intrinsic/Forecast architecture.
- If Candidate A clearly validates and Candidate C supplies coherent calendar ownership, stop expanding complexity.
- Do not merge or deploy from this branch.
