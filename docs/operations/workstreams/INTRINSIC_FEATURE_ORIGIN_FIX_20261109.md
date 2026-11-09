# Intrinsic forecast-origin age correction — 2026-11-09

## Authority and status

User reviewed the positional/feature-origin audit, asked whether a correction was established, then explicitly directed: **“Ok. Make the fix.”** Scope is the demonstrated age handoff defect. No positional adjustment, model-family/route change, calibration/reference-anchor change, production data write, merge or deployment is authorized by this tranche.

**Draft [PR #526](https://github.com/jderhagopian-stack/fsffl-next/pull/526), not live.** Initial tested implementation code head `00b98564d1ed18dfd4113623b7bdab1f1af0469f`, tree `dc607dda1301bd3e28abc38015d208840575e57c` (identical to local `a06639b9`). Follow-up permits a newly evidenced DOB to resolve a new subject without inventing a date for its original age; 65 focused tests cover the final source. The retained reference calculation is unchanged by that new-subject case. CI and Stable promotion gates are not yet claimed. Base main verified `53712984d4a346f587f094877056110138aef02a`; branch `fix/intrinsic-feature-origin-age-20261109`. Existing packaged v1 inputs, accepted source/model code and historical snapshots remain unchanged. Corrected generation has a separate entry point and output identity; it must not silently reuse v1 output identities or replace a saved publication.

## Defect and correction

Completed-source age correctly describes September 1, 2025. The September 19 reconciliation copied that age for 334 shared identities, while computing September 1, 2026 age for its newly added identity. The accepted Y4–Y7 historical feature recipe computes September 1 of the forecast base year. Its current-input builder computed that date correctly, then restored the inherited age. This mismatches the training feature convention and also reaches terminal inputs.

`fsffl.forecast.feature_origin` provides the date-explicit, position/league-independent adapter. It uses governed DOB where available, otherwise advances an explicitly dated source age by elapsed days using the accepted 365.2425-day convention. It never invents a DOB, substitutes zero, uses the current clock or advances experience. Missing/invalid age evidence fails explicitly.

`foundation4_reference_age_origins_2026.json` records recovered source dates and binds them to the exact source age/identity cohort. Its one date override is the original reconciliation's new-identity branch, not a named-player model adjustment. Different cohorts must provide their own explicit age-as-of evidence.

`scripts/materialize_foundation4_forecast_origin.py` creates a new input board with original source-age/date evidence and forecast-origin age. It invokes the unchanged connected-scoring materializer with this board, so both Y4–Y7 and terminal preparation see the corrected age. Materialized forecasts carry the `:forecast-origin-age-v1` version suffix. Output directories must be new; existing inputs/outputs cannot be overwritten. Preparation alone is distinct from completed model materialization.

The manual `foundation4-forecast-origin.yml` workflow exposes this corrected path, defaults to the bounded input gate, and only uploads a separate review artifact. Its explicit `materialize` option runs the existing full materialization; it never commits, promotes or deploys outputs. The original entry point remains an exact v1 reproduction path. New corrected reference generations must use the new entry point. No corrected package is silently accepted by the current v1 consumer: promotion must be explicit and coherent across reference/candidate artifacts.

## Validation

- **65 focused tests passed**, one existing pandas warning. Includes 15 new origin tests plus existing frozen inputs, dynamic candidates, materializer memory, Career aggregation, tail, Shapley and long-horizon tests.
- Real accepted-input preparation retains **335/335 players**: 300 governed DOBs, 35 governed dated-age fallbacks. All original non-age columns, experience, projections and identity/order are preserved. Source ages remain separate fields. 334 ages advance; the original already-current new identity does not.
- Actual accepted feature-builder replay: all 335 corrected ages reach inference; 300 DOB-derived ages agree exactly; no fits in that feature gate. 0.49s locally.
- Additional bounded current Forecast replay used the accepted policy map/69 accepted candidate fits and retained historical calibration. No historical rolling predictions, family selection or route selection were recomputed. Baseline and corrected inputs were evaluated together: **335 players / 5,360 rows per variant**, 57.20s, peak **334,588 KiB**. Baseline versus retained forecasts: max absolute drift **0.00012958**, mean **0.00000347**. Existing documented reproducibility drift remains disclosed; this is not exact bitwise replay.
- Raw economic replay uses **334 matching-State reference players**, not a new 367-player expanded publication. Unchanged 2,048-permutation governed long-horizon consumer: baseline 46.96s, corrected 47.48s; total 94.58s, peak **142,452 KiB**. Baseline versus saved long-horizon raw max drift **0.00020834**; max efficiency residual **1.10e-11**.
- Y1–Y3 inputs/values are unchanged. All-position Career effects below combine recomputed Y4–Y7 and unchanged tail estimators with corrected age. No display or market value was used.

| Reference position | Baseline Career mean | Corrected Career mean | Change |
| --- | ---: | ---: | ---: |
| QB, n61 | 703.053 | 662.158 | -5.82% |
| RB, n88 | 268.625 | 254.615 | -5.22% |
| WR, n121 | 273.104 | 254.124 | -6.95% |
| TE, n64 | 196.611 | 181.450 | -7.71% |

These are reference-subset diagnostics, not full catalog or refreshed production estimates. The correction does not eliminate QB concentration: its share in this subset changes 38.24%→38.41%. It is an input-date fix, not evidence supporting a QB haircut.

## Reproduction

Bounded preparation (no fitting):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python scripts/materialize_foundation4_forecast_origin.py \
  --prepare-only \
  --board artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_CONNECTED_LEAGUE_BOARD_335.csv \
  --players /path/to/accepted/PLAYERS.csv \
  --out-dir /new/private/forecast-origin-inputs
```

For complete artifact generation, omit `--prepare-only` and supply the unchanged accepted materializer's development/route/historical/rules arguments. That full original materialization path can include expensive accepted historical recalibration; the preparation command does not. Do not launch it merely to repeat the already completed bounded tests. The numeric comparison above reused retained calibration and reconstructed current predictions only.

Private reproducibility scripts/outputs are under `/workspace/scratch/intrinsic-feature-origin-resolution-20261108`: `verify_fix.py`, `replay_current_predictions.py`, `replay_reference_values.py`, `FIX_VERIFICATION.json`, `CURRENT_REPLAY_VERIFICATION.json`, `RAW_VALUE_REPLAY_VERIFICATION.json`, full per-player deltas and original audit receipts. No private State, ownership/roster data or raw historical archive is committed.

## Remaining release boundary

The candidate fixes the generation/input handoff. Existing app values remain on their saved v1 artifacts. A corrected full publication needs a coherent versioned reference package, compatible candidate materialization, all current-player coverage, exact-head CI/Stable and separate deployment authorization. The raw comparison covers the 334 reference subjects; it does not reconstruct the discarded expanded-game incumbent results or the 33 captured candidate input boards. Do not claim 367-player corrected production acceptance from it.

No full suite was needed for this draft/local implementation gate; it remains mandatory on the exact stable head before any future merge. No merge or Render action occurred.
