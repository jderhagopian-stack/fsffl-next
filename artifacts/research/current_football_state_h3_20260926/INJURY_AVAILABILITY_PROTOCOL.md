# Injury Availability / Time-to-Return Research Protocol

Date: 2026-09-27  
State: **FROZEN BEFORE MODEL SCORING / RESEARCH ONLY**

## Scope

This phase implements Management's approved current-football-state architecture narrowly.

It may model only:
1. **time to first active-game return** after a contemporaneous injury episode; and
2. **remaining-season participation / availability**.

It must not model or alter:
- conditional healthy production;
- post-return role/opportunity;
- recurrence/reinjury as a causal penalty;
- H2/H3 durable survival or production;
- production H3 or Intrinsic;
- provider ROS authority.

## Historical population

Reuse the already-governed **4,793 injury episodes** from the completed current-football-state historical study.

Episode seasons: 2012–2024.

No injury episode definition, severity label, injury-family mapping, pre-event window, or current-name selection is redefined in this phase.

## Point-in-time predictors

Eligible at the injury-event week:
- position;
- contemporaneous severity class;
- broad injury family derived from contemporaneous injury text;
- event week / structural weeks remaining;
- pre-event fantasy points per active game;
- pre-event opportunity per active game;
- age / NFL experience only if exact PIT values are recoverable from the already-governed career panel.

No post-event role, post-event production, recurrence flag, future roster state, provider revision, Market, Owner, Team Utility, or fantasy transaction information may enter the model.

## Targets

### A. Return timing

A return event is the first active weekly-stat row on or after the injury event week.

- observed return: historical `games_to_return`;
- no observed return that season: right-censored at the remaining regular-season window;
- model output: discrete weekly return hazard and cumulative probability of return by 1, 2, 3 and 4 weeks, plus probability of any same-season return.

This is an **availability** forecast, not a healthy-production forecast.

### B. Remaining-season availability

Historical participation share is explicitly bounded to `[0,1]` before modeling so late-season denominator edge cases cannot create impossible availability.

Model output:
- expected remaining-season active-week share;
- non-zero prediction uncertainty from chronological residuals.

## Baselines

Predeclared comparators:
1. **severity-only empirical baseline** with structural time remaining;
2. **severity + position + injury-family baseline**.

Challengers:
1. regularized linear/logistic model using the full PIT feature set;
2. histogram-gradient-boosting model using the same information set.

The simplest model that clears the gates should be preferred.

## Chronological validation

Final scored holdouts: **2019, 2020, 2021, 2022, 2023, 2024**.

For holdout season `T`:
- train only on episodes with season < T;
- calibrate uncertainty only from prior seasons;
- do not pool future seasons into preprocessing, imputation, category handling, calibration or threshold selection.

No named-player tuning.

## Promotion semantics

A model can earn **Research contract support for the H1 availability component only**.

It does not become provider ROS authority. If governed current ROS is authoritative, the no-double-counting rule still applies and the model must not apply a second H1 haircut.

If ROS authority is absent, an accepted injury-availability model may eventually support a separately authorized fallback availability component while conditional healthy production stays unchanged.

## Prospective archive coupling

The availability model and provider-revision archive remain separate:
- historical injury episodes train availability;
- prospective snapshots preserve future event/provider changes for later causal/incremental studies;
- prospective snapshots are not retroactively inserted into this validation.
