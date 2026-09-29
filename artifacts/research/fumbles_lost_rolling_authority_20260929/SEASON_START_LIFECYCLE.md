# FUMBLES_LOST Season-Start Lifecycle

Date: 2026-09-29  
Authority: **Research contract / bounded implementation handoff**

## Purpose

Close the regular-season lifecycle around the already-accepted Week-2→17 rolling model without inventing an unsupported Week-0 or Week-1 point estimate.

The Week-2→17 rolling mean model, calibration scalars, position rates, role prior, and rolling uncertainty floors are unchanged.

## Completed Week 0 / preseason

There is **no first-party point-estimate authority** for `FUMBLES_LOST`.

Required behavior:
- keep `fum_lost` explicitly omitted from the scored fantasy-point coordinate;
- do not synthesize zero;
- do not reuse the Week-2 mean model without current-season evidence;
- do not claim COMPLETE/FULL player-offense scoring coverage;
- allow downstream continuation only through the corrected `NON_MATERIAL_PARTIAL` materiality gate.

2026 position-wide conservative event bounds, based on all governed completed 2021-2025 player-seasons:

| Position | Week-0 event bound | FSFFL (-1) minimum supported FP stddev |
| --- | ---: | ---: |
| QB | 9.0000 | 54.7161 |
| RB | 4.0000 | 24.3183 |
| WR | 3.0000 | 18.2387 |
| TE | 3.0000 | 18.2387 |

These values are impact bounds only. They are not player Forecasts.

## Completed Week 1

There is still **no first-party point-estimate authority**.

Week-1 opportunity evidence is not sufficient, by this directive, to create a new unvalidated point model. The same explicit-omission behavior applies.

2026 conservative Week-1 bounds:

| Position | Week-1 event bound | FSFFL (-1) minimum supported FP stddev |
| --- | ---: | ---: |
| QB | 9.5625 | 58.1359 |
| RB | 4.2500 | 25.8382 |
| WR | 3.1875 | 19.3786 |
| TE | 3.1875 | 19.3786 |

Historical pseudo-rollover validation across 2023-2025 found **no Week-0 or Week-1 eligible population failures** for history-plus-current, history-only, current-only, or cold-start populations where those tiers exist.

## Transition at completed Week 2

When canonical State advances to completed Week 2:

1. require the target-season annual governed freeze;
2. require provider NFL-state cutoff to equal canonical State;
3. acquire exactly Weeks 1-2 current opportunity evidence;
4. enter the already-supported Week-2 rolling model;
5. use the frozen Week-2 scalar/rates/floors from the target-season production table.

For 2026 this reproduces the accepted v1 Week-2 model exactly.

If the Week-2 supplement cannot be built, do **not** substitute zero. Use the corrected materiality fallback only for an eligible population and only when the runtime impact inequality passes; otherwise fail closed.

## Weeks 3-17

Use the already-frozen rolling model unchanged.

If the point estimate is temporarily unavailable:
- retain explicit omission;
- use the corrected all-population materiality bound;
- respect the population eligibility matrix;
- fail closed when the impact is material or the population is ineligible.

## Week 18 / postseason

Week 18 does not create a new regular-season rolling projection. There is no remaining regular-season window to annualize.

Do not fabricate:
- a Week-18 scalar;
- a zero coordinate;
- a postseason carry-forward pretending to be a regular-season projection.

The next point-authority lifecycle begins with the next target season's governed annual freeze and Week-0 explicit-omission state.

## 2026 historical-boundary note

This lifecycle contract does **not** retroactively create a 2026 preseason Forecast artifact. Existing PIT/preseason provenance rules remain unchanged.
