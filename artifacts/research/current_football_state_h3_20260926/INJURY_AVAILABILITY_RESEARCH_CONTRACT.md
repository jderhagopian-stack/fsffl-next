# Injury Availability Research Contract

Date: 2026-09-27  
Status: **RESEARCH-SUPPORTED COMPONENT / NOT PRODUCTION AUTHORITY**

## Coordinate

`remaining_season_availability`

Definition:
expected fraction of structurally remaining regular-season active opportunities available after a contemporaneously observed injury episode.

Range:
`0.0 <= availability <= 1.0`.

## Research-selected model

Family:
`HistGradientBoostingRegressor`.

Point-in-time inputs:
- position;
- contemporaneous severity class;
- broad injury family;
- event week;
- structural weeks remaining;
- pre-event fantasy points per active game;
- pre-event opportunity per active game;
- age;
- NFL experience.

No post-event feature may enter.

## Output

A future implementation may expose:
- mean remaining-season availability;
- empirical 80% and 90% uncertainty bands;
- provenance: event evidence as-of time, model version, input fingerprint.

The output is an availability coordinate, **not** expected fantasy points by itself.

## Composition

If no authoritative integrated current ROS Forecast exists, a future authorized Forecast fallback may combine:

`remaining H1 expected points = availability × conditional_active_production`

Conditional active production must come from separate governed Forecast evidence.

The availability model must not alter:
- healthy per-active-game production;
- post-return role;
- recurrence;
- H2/H3 survival;
- Intrinsic directly.

## No-double-counting

If authoritative governed current ROS already incorporates current injury availability and role into H1:
- use ROS for H1;
- retain injury availability as explanation/provenance or model-comparison evidence;
- do not multiply ROS by a second availability factor.

## Time-to-return

No precise learned time-to-return model is promoted by this phase.

Direct status/severity evidence may remain coarse explanatory availability evidence. The HistGB return model remains a Research challenger only because its 1.71% endpoint-Brier improvement missed the frozen 2% gate.

## Production prerequisites

A separate Management-authorized production phase would need:
1. current PIT feature acquisition with exact identity/provenance;
2. versioned reproducible model artifact;
3. current-season structural calendar/team-bye semantics;
4. fail-closed handling when injury evidence is missing/ambiguous;
5. explicit ROS no-double-counting routing;
6. hosted/runtime tests;
7. Forecast-output identity invalidation into Intrinsic;
8. no direct Value/Intrinsic injury logic.
