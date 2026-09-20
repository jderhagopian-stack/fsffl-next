# Future Forecast candidate evaluation protocol

## Layer 1 - rolling-origin development / selection

- Freeze the candidate family, parameterization, regularization, conditioning variables, metrics, and gates before running candidate-specific rolling scores.
- Primary origins: Y2 2014-2023; Y3 2014-2022.
- At every origin, fit only on targets fully resolved by T-1 using the exact frozen source reconstruction and model-training rules.
- Use Forecast-wide scoring authority: CRPS/proper distributional score primary, valid Brier/log scores for discrete regions/states, calibration/coverage and tail diagnostics, with raw-point MAE as a guardrail.

## Layer 2 - temporal robustness

- Publish per-origin results.
- Require pooled improvement with clustered uncertainty plus a majority/median origin stability view.
- Publish worst-origin regression and leave-one-origin-out sensitivity.
- For the unresolved developmental-RB Y3 tail, the full cell is primary; continuous magnitude-conditioned calibration and p90+/p95+ influence diagnostics are co-primary structural checks.
- Require low/mid-source and Y2 no-harm checks when the candidate is RB-Y3-specific.

## Layer 3 - fresh confirmation

- Current fully observed Y3 history has no pristine source season beyond 2022.
- Do not call 2021-2022 a pristine holdout again.
- Source 2023 -> Y3 target 2026 should be prospectively frozen as the next true confirmation set and evaluated only after 2026 outcomes are complete.
- Until then, management decisions must rely on nested rolling-origin evidence and explicitly acknowledge the absence of a pristine Y3 external holdout.
- Source 2023 -> Y2 target 2025 may serve as a fresh Y2/no-harm confirmation via rolling-origin refit, but it cannot validate the unresolved Y3 claim.

## Anti-reuse rule

Once a period has informed candidate-family invention or tuning, it may remain in rolling-origin robustness reporting but loses pristine-holdout status. No candidate may be rescued by changing thresholds after seeing its later-origin results.