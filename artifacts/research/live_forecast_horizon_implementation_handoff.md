# FSFFL NEXT — Live Forecast Three-Year Coordinate Implementation Handoff

Status: **RESEARCH HANDOFF ONLY — DO NOT MERGE FROM THIS BRANCH**

Final research disposition: **LIVE THREE-YEAR COORDINATE VALIDATED**.

This file returns the smallest authorized implementation change to management / PR #147. It does not modify PR #147 and does not change production authority.

## Calendar ownership

For a live request during evaluation calendar season `E`, with most recent completed factual source season `S = E-1`:

| Intrinsic year | Calendar target | Forecast authority |
|---|---:|---|
| Year 1 | `E` | existing governed live/current-season Forecast |
| Year 2 | `E+1` | completed-source I1 direct `h=2` (`S+2`) |
| Year 3 | `E+2` | completed-source I1 direct `h=3` (`S+3`) |

Completed-source I1 `h=1` targets calendar `E`. It remains diagnostic/reference only in the live three-year composition. It must not be relabeled as Year 2 and must not be added to the Shapley total.

Example for a live 2026 request:

```text
completed factual source S = 2025
live evaluation season E   = 2026

Year 1 / 2026 = governed live/current-season Forecast
Year 2 / 2027 = completed-2025 I1 h=2
Year 3 / 2028 = completed-2025 direct I1 h=3

completed-2025 I1 h=1 -> 2026 diagnostic only
```

## Minimal authorized changes inside PR #147

1. **Do not replace the existing live current-season Forecast.** It remains the Year-1 authority.
2. **Extend the frozen I1 completed-season model to direct `h=3`.** Use the same I1 architecture, feature/evidence semantics, global `C=0.25`, persistence + ordered conditional-state decomposition, state-conditional production means, minimum-fit/fallback governance, and source provenance. Train `h=3` directly against factual `S+3`; do not recurse through `h=1`/`h=2` predictions.
3. **Expose direct `h=3` probabilities, state means, anticipated production, model path and horizon metadata** alongside existing direct horizons. The horizon label must remain `3` and target season must be computed as `source_season + 3`.
4. **Compose the live Intrinsic vector by calendar authority, not by positional array relabeling.** The Shapley consumer receives Year 1 from live/current-season Forecast, Year 2 from I1 `h=2`, and Year 3 from I1 `h=3`.
5. **Explicitly exclude completed-source `h=1` from the live Shapley sum.** It may remain available for diagnostics/parity because it targets the same calendar year as the live Year-1 Forecast.
6. **Keep frozen Shapley economics unchanged:** 2,048 permutations, seed `20260915`, discount `0.85`, W unchanged, B4 unchanged, and all ten Constitution principles unchanged.
7. **Add calendar-coherence tests** proving:
   - `h=1 == S+1`, `h=2 == S+2`, `h=3 == S+3`;
   - with `S=E-1`, live Year 1=`E`, I1 `h=2`=`E+1`, I1 `h=3`=`E+2`;
   - completed-source `h=1` is not double-counted;
   - no recursive I1 call is used to generate `h=3`;
   - no partial active-season facts are treated as a completed source season.
8. **Preserve horizon-specific uncertainty.** The research evidence shows error and entropy increase with horizon. Do not advertise Year 3 with the same apparent certainty as Year 1/2. Any future production interval must be calibrated from horizon-specific residual evidence rather than an arbitrary multiplier.
9. **Preserve Forecast input boundaries.** No market values, dynasty rankings, trades, fantasy ownership, owner behavior, Team Utility, Decision/Search, Shapley or Value output becomes a Forecast predictor.

## Research cautions implementation should retain in metadata / monitoring

- The direct `h=3` confirmation improved overall state Brier, state log loss, useful/starter/premium Brier, production MAE/RMSE and absolute bias versus the empirical direct-transition baseline.
- Persistence Brier was slightly worse in confirmation.
- QB production accuracy improved but showed a conservative average bias in confirmation.
- RB state calibration was slightly worse while production MAE improved.
- TE was modestly worse on state/log-loss/MAE in the single untouched confirmation fold even though TE improved over the broader rolling selection history. Treat this as a monitoring caution, not a reason to introduce a TE-specific model or coefficient.
- Do not add subgroup patches unless separately researched and authorized.

## Downstream validation after Forecast freeze

The frozen PR #147 Shapley consumer was tested only after the Forecast coordinate was frozen:

- 2,048-permutation calendar-alignment diagnostic: PASS.
- Formula reconciliation `Y1 + 0.85*Y2 + 0.85^2*Y3`: exact residual `0.0` in the anonymous diagnostic fixture.
- Completed-source `h=1` double-count check: PASS.
- Year-3 uncertainty greater than Year-2 uncertainty in the diagnostic fixture: PASS.
- Locked 10-point Intrinsic Constitution: all ten principles PASS; conclusion remains `A1. SHAPLEY SATISFIES THE INTRINSIC CONSTITUTION AS A PROMISING CARDINAL CHALLENGER`.

## What is not authorized

- No merge/deploy from the research branch.
- No relabeling `h=1` as 2027 in a 2026 live view.
- No recursive forecast chaining.
- No extrapolated `h=2` coefficients/state means masquerading as `h=3`.
- No in-season PIT future model until genuine historical or prospectively accumulated snapshot evidence exists.
- No change to I1 family, `C=0.25`, Shapley W, discount, B4, market coordinates, Team Utility, Decision or Search from this handoff.
