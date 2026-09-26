# Long-Horizon Age / Experience / Career-Exposure Audit Freeze

Date: 2026-09-26  
State: **FROZEN BEFORE TRAJECTORY-AUDIT RESULTS**

This audit is part of the active cell-routing corrective. It does not reopen production H3 and does not consume current named-player results.

## Questions

For QB/RB/WR/TE at Y4-Y8, test separately:
1. chronological age at the target season;
2. NFL experience at the target season;
3. accumulated prior NFL exposure/workload;
4. interactions between target age/experience, cumulative exposure, recent role/production and horizon;
5. survival/relevance probability versus conditional production when active.

## PIT cumulative features

All career exposure is computed using seasons strictly before the base forecast season.

Universal:
- career games;
- seasons with games;
- cumulative opportunities;
- cumulative fantasy production.

QB:
- cumulative pass attempts;
- cumulative estimated dropbacks = attempts + sacks suffered;
- cumulative carries.

RB:
- cumulative carries;
- cumulative targets;
- cumulative receptions;
- cumulative touches = carries + receptions;
- cumulative opportunities = carries + targets.

WR/TE:
- cumulative targets;
- cumulative receptions;
- cumulative carries;
- cumulative opportunities = targets + carries.

Routes are not assumed because governed historical route data is not present in the retained panel.

## Target-horizon transformations

For horizon H:
- age_at_target = base age + H - 1;
- experience_at_target = base NFL experience + H - 1;
- squared/cubic target-age terms;
- squared target-experience term;
- log1p cumulative workload terms;
- workload per prior NFL season;
- recent-to-career workload share;
- target-age × log workload;
- target-experience × log workload.

No manual age cliff or dynasty-age bonus is specified.

## Frozen model variants

All variants retain the governed Forecast10 trajectory terms other than the age/experience substitution being tested.

1. `base_linear`
   - inherited base-season age + experience;
   - two-part ridge.

2. `target_poly`
   - target-horizon age/experience with polynomial nonlinearities;
   - two-part ridge.

3. `target_poly_exposure`
   - target nonlinear age/experience + cumulative workload + recent/career interactions;
   - two-part ridge.

4. `target_exposure_histgb`
   - same target-age/experience/exposure information;
   - nonlinear two-part gradient boosting.

5. `exposure_ablation`
   - target nonlinear age/experience + recent role but without cumulative exposure;
   - two-part ridge.
   - compared against target_poly_exposure to isolate incremental accumulated workload.

## Validation

Use the corrected cell-routing workflow's frozen repeated rolling-origin plan:
- selector inputs are historical only;
- no prior final-holdout artifact is consumed;
- no current named-player shadow is consumed;
- no year is relabeled untouched;
- Y8 remains limited to two valid outer origins and therefore cannot earn exact new authority from this audit alone.

For each position × horizon × model variant report:
- overall RMSE / MAE / bias / Spearman / tail RMSE;
- survival Brier, calibration gap and active-rate bias;
- conditional-production RMSE / MAE / bias / Spearman among actually active rows;
- rolling-origin win/stability;
- era sensitivity;
- sample support and exposure coverage.

## Interpretation rule

An age/exposure extension is considered materially supported only when it:
- improves the relevant decomposed component in repeated outer validation;
- does not create a material overall/tail regression;
- is stable across a majority of available outer origins;
- has adequate support in the position × horizon cell.

If survival improves but conditional production does not, preserve that distinction. If cumulative workload adds no stable information beyond age/experience/recent role, do not retain it merely because it sounds intuitive.

No production age penalty, youth bonus or manual curve is authorized.
