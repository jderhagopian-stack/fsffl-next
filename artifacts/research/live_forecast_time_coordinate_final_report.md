# FSFFL NEXT - Live Forecast Time Coordinate & Horizon Final Research Report

**Status:** RESEARCH ONLY - FINAL HANDOFF  
**Final disposition:** **LIVE THREE-YEAR COORDINATE VALIDATED**  
**Research PR:** #150 (`research/live-forecast-time-coordinate-horizon`)  
**Production authority changed:** No  
**Implementation PR #147 modified by this research:** No

## 1. Executive summary

FSFFL had a real calendar mismatch in its live three-year Intrinsic construction. During a live 2026 evaluation, the last completed season is 2025. Completed-season I1 therefore maps `h=1` to 2026 and `h=2` to 2027. Those two direct horizons cannot honestly populate 2026, 2027 and 2028 by relabeling. This workstream was created to resolve that mismatch without recursion, horizon relabeling, partial-season-as-completed shortcuts, or downstream Value/Shapley tuning.

The research supports a clean solution:

- **Calendar Year E / Year 1:** existing governed live/current-season Forecast.
- **Calendar Year E+1 / Year 2:** completed-source I1 direct `h=2`.
- **Calendar Year E+2 / Year 3:** completed-source I1 direct `h=3`.
- Completed-source I1 `h=1` remains a same-calendar-year diagnostic/reference only and is **not** double-counted.

A direct non-recursive `h=3` I1 extension at the already-governed global `C=0.25` showed modest but coherent improvement in rolling 2014-2020 selection history and then improved again on the mechanically gated untouched source-2021 -> target-2024 confirmation. After Forecast was frozen, the existing 2,048-permutation Shapley consumer reconciled exactly under the new calendar ownership, and the locked ten-point Intrinsic Constitution continued to pass all ten principles.

No new model family, tuning coefficient, market input, owner input, trade input, Team Utility input, or named-player optimization was introduced.

## 2. The calendar problem

For a live request in evaluation season `E`, the last completed factual source season is `S = E-1`.

| Coordinate | Real calendar target | Authority after this research |
|---|---:|---|
| Intrinsic Year 1 | `E` | Existing governed live/current-season Forecast |
| Intrinsic Year 2 | `E+1` | Completed-source I1 direct `h=2` (`S+2`) |
| Intrinsic Year 3 | `E+2` | Completed-source I1 direct `h=3` (`S+3`) |
| Diagnostic only | `E` | Completed-source I1 `h=1` (`S+1`) |

### Concrete 2026 example

```text
Completed factual source season S = 2025
Live evaluation season E          = 2026

Year 1 / 2026 = governed live/current-season Forecast
Year 2 / 2027 = completed-2025 I1 h=2
Year 3 / 2028 = completed-2025 direct I1 h=3

Completed-2025 I1 h=1 -> 2026 diagnostic/reference only
```

The key governance point is that model horizons retain their literal meanings. `h=1` is never relabeled as 2027, and an I1 prediction is never recursively fed back into I1 to manufacture a farther horizon.

## 3. Phase-A authority audit

The audit identified three separate authorities that must remain separate:

1. **Live/current-season Forecast** - a governed current-season authority using as-of-week actual production plus remaining projection evidence. It can legitimately own the active calendar season.
2. **Completed-season I1** - the frozen persistence/state Forecast architecture using completed factual source-season evidence. Before this study, it directly supported `h=1` and `h=2`.
3. **Shapley/Intrinsic consumer** - the frozen economic allocation layer. It consumes Forecast outputs but cannot define or tune Forecast calendar semantics.

This separation matters because the calendar problem could not be solved downstream by Value or Shapley without violating authority boundaries.

## 4. Candidate audit and pre-results exclusions

### Candidate A - direct completed-season `h=3`

**Tested.** The same I1 architecture was extended to learn a direct `S -> S+3` factual target. It retained global `C=0.25`, the persistence-first decomposition, ordered conditional state thresholds, rich/reduced evidence paths, state-conditional production means, and the existing minimum-fit/fallback governance.

### Candidate B - genuine historical in-season PIT future Forecast

**Excluded before results were inspected.** FSFFL has appropriate prospective append-only projection-history infrastructure, but the live `fsffl.projection_snapshot` table contained **zero rows** at the pre-results audit. The durable projection-history migration was introduced on September 11, 2026. There is therefore no internal historical 2014-2025 weekly/provider snapshot archive from which to reconstruct honest historical as-of-date projection beliefs.

Backfilling later-observed projections would create leakage. Candidate B should be revisited only after sufficient prospective snapshots accumulate or after a separately verified/licensed historical archive is obtained.

### Candidate C - governed calendar-ownership hybrid

**Accepted as a semantic composition after Candidate A validated.** It is not another predictive model. It simply assigns each real calendar season to the correct already-governed Forecast authority.

## 5. Frozen research design

The direct `h=3` selection was fixed before results:

- Architecture: I1.
- Global regularization: `C=0.25`.
- No developmental override.
- Rolling selection source seasons: **2014-2020**.
- Untouched confirmation: **source 2021 -> target 2024**.
- Strict chronological fitting: a training target had to be knowable before the evaluation source season.
- Baseline: empirical direct three-year transition prior built from the same point-in-time training rows.
- `h=1` and `h=2`: context only, not reopened for model-family selection.
- No live 2026 player outcomes were used.
- No Shapley, Value, market, owner, trade, fantasy ownership, Team Utility, Decision or Search output could select Forecast.

The untouched confirmation workflow was mechanically gated behind a committed selection-freeze artifact. The downstream Shapley workflow was separately gated behind a committed final Forecast freeze.

## 6. Rolling selection evidence: direct `h=3`

Across **2,479 resolved** selection forecasts, direct I1 `h=3` improved the broad state forecast and production error versus the empirical direct-transition baseline.

| Metric | Empirical baseline | Direct I1 `h=3` | Direction |
|---|---:|---:|---|
| State Brier | 0.13483 | **0.13444** | Better |
| State log loss | 1.75138 | **1.74419** | Better |
| Production MAE | 53.98 | **52.34** | Better |
| Production RMSE | 76.04 | **74.63** | Better |
| Starter Brier | 0.23682 | **0.23374** | Better |
| Premium Brier | 0.22784 | **0.22125** | Better |
| Persistence Brier | **0.10301** | 0.10333 | Slightly worse |
| Useful Brier | **0.21255** | 0.21320 | Slightly worse |
| Production bias | -7.03 | -9.38 | More conservative |

The earliest rolling folds did not yet have enough direct three-year training history to fit I1 and therefore fell back to the empirical baseline. The three genuinely fitted selection folds were source 2018, 2019 and 2020.

| Source -> target | Production MAE change | State Brier change | State log-loss change |
|---|---:|---:|---:|
| 2018 -> 2021 | **-4.91** | +0.00006 | +0.01003 |
| 2019 -> 2022 | **-3.62** | **-0.00185** | **-0.03739** |
| 2020 -> 2023 | **-2.40** | **-0.00079** | **-0.01894** |

Lower is better. Production MAE improved in every fitted fold; state calibration improved in two of the three and was only slightly worse in the first fitted fold. This was sufficient to advance the candidate to confirmation, but not sufficient to declare it final before the untouched fold.

## 7. Developmental and temporary-absence safety

The direct `h=3` candidate did not create the developmental false-optimism problem the project has been guarding against.

- Developmental successes in selection history: 111.
- Baseline true hits: 108; direct I1 true hits: **109**.
- Baseline false positives: 111; direct I1 false positives: **109**.
- Developmental state Brier improved from 0.14066 to **0.13957**.

Temporary-absence state safety was essentially stable: state Brier improved slightly from 0.13434 to **0.13426**, while persistence Brier worsened slightly from 0.09641 to 0.09697.

## 8. Horizon degradation and uncertainty

The study also confirms that farther forecasts are intrinsically harder. The same direct I1 family shows rising production error and state uncertainty as the horizon extends.

| Direct horizon | Resolved n | State Brier | State log loss | Production MAE | Mean state entropy |
|---|---:|---:|---:|---:|---:|
| `h=1` | 3,588 | 0.12131 | 1.52353 | 39.85 | 1.43277 |
| `h=2` | 3,088 | 0.12977 | 1.69713 | 45.45 | 1.54416 |
| `h=3` | 2,479 | 0.13444 | 1.74419 | 52.34 | 1.63810 |

This means Year 3 must not be presented with the same implied certainty as Year 1 or Year 2. Any future confidence interval should be calibrated from horizon-specific residual evidence rather than an arbitrary multiplier.

## 9. Untouched source-2021 -> target-2024 confirmation

After the pre-confirmation selection decision was committed, the untouched fold was opened. It contained **392 resolved** and **222 unresolved** candidate rows.

The direct `h=3` candidate confirmed the selection signal:

| Metric | Baseline | Direct I1 `h=3` | Relative change |
|---|---:|---:|---:|
| State Brier | 0.12681 | **0.12515** | **-1.31%** |
| State log loss | 1.59183 | **1.58179** | **-0.63%** |
| Production MAE | 44.61 | **42.91** | **-3.81%** |
| Production RMSE | 63.16 | **60.72** | **-3.85%** |
| Useful Brier | 0.20801 | **0.20097** | **-3.38%** |
| Starter Brier | 0.20472 | **0.19950** | **-2.55%** |
| Premium Brier | 0.17308 | **0.16417** | **-5.14%** |
| Persistence Brier | **0.09426** | 0.09509 | +0.88% |
| Production bias | +4.87 | **+3.20** | Closer to zero |

Developmental confirmation was also coherent: both approaches caught 6 of 7 successes, while direct I1 reduced false positives from 17 to **15** and improved developmental state Brier.

Temporary-absence state Brier improved from 0.12689 to **0.12540**; persistence Brier again worsened slightly.

### Confirmation cautions

The confirmation was positive, but not every subgroup improved on every metric:

- **QB:** production MAE and state quality improved, but average production bias became about 7 points conservative.
- **RB:** production MAE improved while state Brier/log loss were slightly worse.
- **TE:** state Brier, log loss and production MAE were modestly worse in this one confirmation fold, despite TE improving over the broader rolling selection history.
- **Persistence Brier:** slightly worse overall in both selection/confirmation even while broader state, threshold and production accuracy improved.

These are monitoring cautions, not evidence for new position-specific models or coefficients. No subgroup patch is authorized by this study.

## 10. Final Forecast selection

The predeclared Forecast criterion was a coherent, repeatable advantage without material subgroup safety failure, followed by coherent untouched confirmation.

Direct `h=3` satisfies that standard:

- production MAE improved in all genuinely fitted selection folds;
- aggregate selection state calibration and production error improved;
- the untouched confirmation improved state Brier, state log loss, useful/starter/premium Brier and production MAE/RMSE;
- developmental false optimism did not worsen;
- temporary-absence state safety remained coherent;
- subgroup reversals were modest and mixed rather than a repeatable material safety failure;
- no live 2026 result was used to select or validate the model.

**Final Forecast disposition: LIVE THREE-YEAR COORDINATE VALIDATED.**

## 11. Post-freeze Shapley calendar test

Only after the Forecast coordinate was frozen did the study inspect the downstream economic consumer.

The existing authoritative PR #147 Shapley implementation was checked using an anonymous 128-player fixture under the frozen league structure. No named-player outcome could influence the test.

Frozen constants remained unchanged:

- Monte Carlo permutations: **2,048**.
- Seed: **20260915**.
- Career discount: **0.85**.
- W / structural scarcity architecture: unchanged.
- B4: unchanged.

All calendar/economic sanity checks passed:

- exact formula `Year1 + 0.85*Year2 + 0.85^2*Year3`: **PASS**, maximum residual **0.0**;
- finite outputs: **PASS**;
- nonnegative outputs: **PASS**;
- completed-source `h=1` absent from live value sum: **PASS**;
- Year-3 state entropy >= Year-2 entropy: **PASS**.

The anonymous diagnostic showed mean state entropy of 1.6719 for Year 2 and 1.7213 for Year 3, preserving the intended longer-horizon uncertainty direction.

## 12. Locked Intrinsic Constitution

The locked ten-point Intrinsic Constitution was rerun unchanged after the Forecast freeze. All ten principles passed:

1. useful players have positive intrinsic value;
2. scarcity matters;
3. elite players separate disproportionately;
4. zero-use players can be exactly zero;
5. credible future rights have value;
6. generic variance is not rewarded by itself;
7. league format changes value structurally;
8. intrinsic value remains roster-neutral;
9. B4 holding-right separation remains intact;
10. market independence remains intact.

The conclusion remains:

**A1. SHAPLEY SATISFIES THE INTRINSIC CONSTITUTION AS A PROMISING CARDINAL CHALLENGER.**

This downstream result did not select or tune Forecast; it merely confirmed that the frozen Forecast calendar coordinate is compatible with the already-frozen economic architecture.

## 13. Exact implementation handoff to PR #147

The smallest authorized implementation change is:

1. Keep the existing live/current-season Forecast as live **Year 1** authority.
2. Extend completed-season I1 to a **direct `h=3`** using the same architecture and global `C=0.25`.
3. Expose direct `h=3` probabilities, state means, anticipated production, model path and exact target-season metadata.
4. Compose the live three-year Intrinsic vector by **calendar target**, not array position:
   - Year 1 = live/current-season Forecast for `E`;
   - Year 2 = completed-source direct `h=2` for `E+1`;
   - Year 3 = completed-source direct `h=3` for `E+2`.
5. Keep completed-source `h=1` diagnostic only and explicitly exclude it from the live Shapley sum.
6. Leave 2,048 permutations, seed 20260915, discount 0.85, W, B4 and all Constitution principles unchanged.
7. Add tests proving direct calendar alignment, absence of double counting, absence of recursion, and absence of partial-season-as-completed inputs.
8. Preserve horizon-specific uncertainty and monitoring for QB bias, RB state calibration, TE confirmation stability, and persistence Brier.
9. Do not introduce position-specific patches without separate research.
10. Do not introduce market, owner, trade, roster-fit, Team Utility, Decision/Search or Value outputs into Forecast.

## 14. What this research does not authorize

- No merge or deploy from research PR #150.
- No automatic merge of implementation PR #147.
- No change to I1 family or global `C=0.25`.
- No recursive Forecast chaining.
- No relabeling of `h=1`/`h=2` horizons.
- No synthetic 2028 coordinate if direct `h=3` is unavailable.
- No in-season PIT future model until genuine historical/prospective snapshot evidence exists.
- No change to Shapley W, discount 0.85, B4, market coordinates, Team Utility, Decision or Search.

## 15. Limitations

- The earliest direct `h=3` rolling folds lacked sufficient training history to fit I1 and fell back to the empirical prior; only the 2018-2020 selection folds are genuinely fitted direct-I1 comparisons.
- The untouched confirmation has one target season (2024) and 392 resolved rows. It is meaningful but not an unlimited sample.
- Some subgroup metrics reverse in the confirmation fold, especially TE state/production metrics and RB state calibration.
- Persistence Brier is consistently slightly worse even when overall state/threshold and production metrics improve.
- Historical in-season projection snapshots do not exist internally yet, so a more fully PIT in-season future-season model remains a future research opportunity rather than a current capability.
- Commercial readiness of upstream factual data remains governed by the project's existing data-provenance/licensing review. This work introduces no new external commercial dependency.

## 16. Repository state at final handoff

As verified on September 16, 2026:

- Production `main`: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76` - unchanged by this workstream.
- Authoritative implementation PR #147: open, draft, unmerged, head `b36328ebf3af6f435282e5930f3b72b681a8f857` at final verification - not modified by this research workstream.
- Research PR #150: open, draft, unmerged; research branch `research/live-forecast-time-coordinate-horizon`.
- Forecast final-freeze commit: `744952af01140daa0cbdbff9b0683018d4db0e0d`.
- Research handoff commit before this report: `b3cda2a1005d72f0defb243a41de15e2881b7015`.
- Downstream calendar/Shapley workflow run `35052625992`: completed successfully.
- No production authority was changed.

## 17. Final conclusion

The original calendar concern was real: completed-2025 I1 `h=1` and `h=2` cannot honestly be called 2027 and 2028 during a live 2026 evaluation.

The research resolves that problem without changing the architecture's governing principles. FSFFL can support an honest live three-year Intrinsic vector by giving the active calendar season to the existing live Forecast and adding one empirically validated direct completed-season horizon for the far year.

**Final disposition: LIVE THREE-YEAR COORDINATE VALIDATED.**

The management/implementation action is narrow: carry the calendar ownership contract and direct `h=3` extension into authoritative PR #147, preserve all frozen economic constants and authority boundaries, and retain the documented uncertainty/subgroup monitoring cautions.
