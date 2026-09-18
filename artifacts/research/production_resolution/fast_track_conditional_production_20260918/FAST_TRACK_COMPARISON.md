# FSFFL NEXT — Fast-track conditional-production repair checkpoint

Date: 2026-09-18

## Scope
Bounded research under Management Fast-Track Conditional-Production Repair. No main/PR #147/production/Shapley/Intrinsic changes.

## Stage 0 coordinate sanity
PASS with a correction to the prior retention diagnostic.

The preserved Y1 field is a governed 2026 season projection from `fsffl:live_league_scored[fsffl:live_equal_weight]:empirical-season-uncertainty`, model version `next2-current-runtime-v4:parallel-provider-ingestion:independent_metric_variance:next2-live-season-fp-uncertainty-v1`. It is not 2025 realized/source production.

The earlier sentinel values such as Bijan Robinson 299.8 are completed 2025 source-season fantasy points used by the frozen future-state machinery. The governed Y1 values such as Bijan 479.9, Jahmyr Gibbs 460.25 and Puka Nacua 401.5 are projected 2026 league-scored values.

The prior diagnostic compared current Y2/Y1 to historical source→Y+1. The correct sequential historical analog is realized Y+2 / realized Y+1 (and Y+3 / Y+1) from the same PIT source. Recomputed without changing Forecast:
- all current median Y2/Y1 49.7%; historical sequential Y+2/Y+1 60.9%
- all current median Y3/Y1 40.3%; historical sequential Y+3/Y+1 26.6%
- age<=25 current 53.5% / 44.0%; historical 70.5% / 49.0%
- current top-10% within-position 46.8% / 36.7%; historical upper-tail 88.1% / 75.9%
- current top-5% 47.9% / 40.0%; historical 88.2% / 80.3%
- prime 26–29 + top-quartile current 47.6% / 35.2%; historical 81.6% / 55.6%

Conditional on remaining active, current top-10% conditional production/Y1 is 51.4% / 45.6%, versus historical sequential active medians 90.0% / 83.0%. The upper-tail conditional-production defect therefore survives the coordinate correction.

## Three bounded candidates
Historical PIT only; chronological rolling-origin folds. True current rookies/cold-starts were not mixed into NFL-history retention fitting.

- A: regularized continuous conditional-retention model.
- B: regularized direct conditional-active points model using position, source magnitude/percentile, age, experience, state, and genuine prior-history coverage.
- C: historically learned cell gate choosing B only where chronologically earlier evidence beat A; otherwise A.
- simple carry-forward retained as a comparison baseline.

Final 2021–2022 holdout conditional-active MAE:
- Y2 overall: A 40.02; B 39.60; C 40.03; carry-forward 45.28
- Y3 overall: A 42.00; B 41.89; C 42.01; carry-forward 48.80
- Y2 top-10%: A 57.35; B 55.11; C 57.35; carry-forward 72.28
- Y3 top-10%: A 56.93; B 55.33; C 56.93; carry-forward 75.04
- Y2 prime/high: A 54.76; B 51.79; C 54.76; carry-forward 66.21
- Y3 prime/high: A 50.96; B 49.73; C 50.96; carry-forward 78.01

Candidate B chronological overall MAE:
- early: 41.05 Y2 / 43.03 Y3
- mid: 43.60 / 46.25
- validation: 39.50 / 40.39
- holdout: 39.60 / 41.89

Holdout median retention, Candidate B:
- age<=25: 86.9% predicted vs 88.5% actual Y2; 84.8% vs 87.8% Y3
- top-10%: 61.8% vs 72.9% Y2; 53.4% vs 71.0% Y3
- top-5%: 60.2% vs 69.3% Y2; 50.6% vs 68.5% Y3
- prime/high: 51.6% vs 69.6% Y2; 46.2% vs 48.2% Y3

Role-loss stress holdout MAE:
- A 28.50 Y2 / 29.18 Y3
- B 29.07 / 30.03
- C 28.91 / 29.43
- carry-forward 56.42 / 56.00

## Fast decision rule
Candidate B is the strongest of the three but **none clears the predeclared advance bar**. B improves overall and upper-tail accuracy and materially repairs young-player conditional retention, but still under-retains the upper tail, especially at Y3, and is slightly worse than A on role-loss stress.

Therefore no candidate is advanced as a production repair. Candidate B is the evidence-leading mechanism if management authorizes one more narrowly bounded refinement. No new feature-search tree is opened here.

## Stop
STOP for management review. No Shapley/Intrinsic redesign, C=0.25 change, persistence/routing redesign, named-player tuning, external-data research, main/PR #147 modification, merge, deploy, promotion, or implementation.
