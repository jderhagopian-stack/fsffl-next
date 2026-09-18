# FSFFL NEXT — B3 two-regime conditional-production checkpoint

Date: 2026-09-18

## Scope
Final bounded B3 test only. Candidate B baseline retained. Persistence, state routing/probabilities, exact-age machinery, cold-start separation, identity/materialization, Shapley/Intrinsic, C=0.25 and previously rejected families were not changed.

## Predeclared B3 specification
Within historically active rows, role retained was defined before evaluation as: target production >=75% of source production OR target state rank >= source state rank. Complement is the active deterioration regime.

P(role retained | active) used only existing PIT source features: position, horizon, log source production, within-position/source-season production percentile, age, experience, source state, prior-history coverage, and current/prior age-state residuals. Gate: regularized logistic regression (C=0.25). Separate regularized Ridge(alpha=10) log-point regressions estimated retained-role and role-loss production; final conditional-active production was their probability-weighted mixture.

Selection evidence was limited to pre-holdout chronological folds: early 2014–2016, mid 2017–2018, validation 2019–2020. 2021–2022 was secondary/non-pristine replication only.

## Result
DO NOT ADVANCE B3.

The role-retention gate is genuinely informative rather than noise: pre-holdout AUC is stable at approximately 0.684–0.696 with aggregate calibration gaps approximately 0.7–4.5 percentage points.

B3 improves top-10% MAE versus B in every pre-holdout fold/horizon comparison, but materially worsens genuine role-loss MAE in every comparison:
- early Y2: 33.85 -> 48.06
- early Y3: 30.93 -> 45.61
- mid Y2: 32.66 -> 45.81
- mid Y3: 40.76 -> 61.46
- validation Y2: 32.78 -> 49.09
- validation Y3: 30.47 -> 46.54

Young-player retention is pushed too high and young MAE worsens in most pre-holdout comparisons.

The non-pristine 2021–2022 block again shows upper-tail improvement, but it was not used for selection and does not override the hard-stop failure.

## Management recommendation
Choose option (b): leave Forecast on hold for a future larger redesign. Candidate B is more stable, but its documented upper-tail conservatism is the confirmed horizon-shape defect. B3 shows that durable-role separation is real and partially predictable, but the bounded source feature set does not discriminate strongly enough to safely allocate retained-role production.

No B3 model was frozen. Therefore no current 335-player B3 board was generated.

## Stop
No production promotion, implementation, merge, deploy, main modification, PR #147 modification, Shapley redesign, or further model research was performed.
