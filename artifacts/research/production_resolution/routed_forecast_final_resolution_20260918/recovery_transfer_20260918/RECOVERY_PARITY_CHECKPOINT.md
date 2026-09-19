# Routed Forecast recovered-artifact transfer — recovery parity checkpoint

Date: 2026-09-18  
Authority: recovery only  
Outcome: **A — RECOVERY PARITY PROVEN; STAGE 0 COMPLETE**

## Protected live state

Before recovery, the live research branch was re-fetched and remained exactly at the prior Outcome-C head:

- research branch: `research/future-state-resolution-phase34-resume`
- starting head: `1ae54cb4012e68bec8b39445eeaf8033728e48cd`
- main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #147: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`

No protected ref was modified.

## Library discovery

All four exact artifacts named by management were recovered from the user's `/FSFFL NEXT` Library. No manual attachment was required.

| Artifact | Original Library file id | Bytes | SHA-256 |
|---|---|---:|---|
| `recombination_prediction_rows.csv` | `file_00000000af4081f5b9a6e5cc41359ac0` | 16,071,418 | `dbd1b1b5fd7fe7c6c43c2e6bda417db192c852f136ac704a7a5abb48fae2288b` |
| `hybrid_prediction_rows.csv` | `file_000000004f7081f5b2fff363d0ba7acc` | 2,411,645 | `67e1306982074c91bc666daed306ad688cbfa90dd8c73d59087cd8b770707fb2` |
| `corrected_aligned_candidate_rows.csv` | `file_00000000f14c81f5a4208c822326a29f` | 3,956,615 | `2c5878a431523cf0f33b5d29a48585324318d97b1b615a16ce0c1aa4f167277e` |
| `b2_prediction_rows.csv` | `file_00000000d95881f5ab25ebd83dbcd3ef` | 3,753,657 | `9eda45f36786c0c73a190566b9eb14d199a604427112c890488f2d5a2cdaacb6` |

The recombination file's raw-byte SHA-256 is an exact match to the hash recorded by the earlier provenance audit. Its row count is exactly 41,344 and its candidate set is B / FrozenForecast / R1 / R2.

## Exact candidate-coordinate parity

The recovery used key:

`fold, horizon, source_season, player_id, position`

The legal pre-holdout aligned coordinate contains 4,287 B2a rows, 4,287 R1 rows and 4,287 R2 rows on identical keys, with zero duplicate keys.

H2 contains 2,553 rows and is an exact subset of that coordinate. Its 1,734 absent early-fold rows are not a recovery defect: the original hybrid checkpoint explicitly states that no leakage-free hybrid-training block existed before the early fold, so H2 was evaluated only at mid and validation.

Prediction parity against the original source artifacts:

- corrected B2a vs B2 artifact: 4,287 / 4,287 joined, no missing keys, max absolute prediction delta `5.68e-14`;
- corrected R1 vs active-row recombination R1: 4,287 / 4,287 pre-holdout joined, max delta `2.84e-14`;
- corrected R2 vs active-row recombination R2: 4,287 / 4,287 pre-holdout joined, max delta `5.68e-14`;
- corrected H2 vs hybrid H2: 2,553 / 2,553 joined, no missing keys, max delta `2.84e-14`.

This is floating-point parity. No predictions were rebuilt.

## Durable metric parity

Recovered rows reproduce the existing repository checkpoints:

### Corrected B2a selection
- Y2 B MAE: 41.37956; B2a: 41.08931.
- Y3 B MAE: 43.12948; B2a: 42.58420.
- Y2 top-10 MAE: 61.24687 -> 60.32937.
- Y3 top-10 MAE: 60.62429 -> 59.88761.
- Y2 role-loss MAE: 32.84058 -> 34.46330.
- Y3 role-loss MAE: 32.64845 -> 35.12782.

These round exactly to the values recorded in the corrected-selection checkpoint.

### B2 fold role-loss stress
Every early/mid/validation Y2/Y3 B-to-B2a role-loss number reproduces the B2 bounded-refinement checkpoint to its published precision.

### H2 hybrid
Every mid/validation Y2/Y3 overall, top-10 and role-loss MAE for B and H2 reproduces the final hybrid checkpoint to its published precision.

## Historical-coordinate caution preserved

The recovered studies do not use one identical definition of every derived percentile flag. In particular, candidate-specific `source_pct` / top-10 / top-5 fields can differ because their historical study universes differed.

Recovery therefore does **not** choose a canonical career-state percentile definition. Common source-time player identity, position, age, experience, source state, source production and target outcome align. Any later career-state definition must be frozen under the original Routed Forecast directive rather than inferred during recovery.

## Durable preservation

Manifest commit: `e60628384811ac1c9882c3c9c76be3b616fc7063`.

The manifest records the exact original Library paths, stable file/library identifiers, raw sizes and SHA-256 hashes for all four authoritative artifacts. The original bytes remain losslessly stored in `/FSFFL NEXT`, so a later chat can retrieve the precise artifacts directly rather than relying on a filename-only search or repository summary.

A deterministic 4,287-row compact aligned coordinate was also produced from the recovered exact rows only:
- name: `routed_forecast_aligned_candidate_coordinate_compact_v1.csv`
- rows: 4,287
- columns: 18
- SHA-256: `8095788e1b48028c50b65d7fba51ac48a41daceeaa6459ae3a219723ce30b1eb`

It is a transfer convenience, not a newly fitted model or a replacement for the source artifacts.

## Outcome and continuation boundary

**Outcome A. The original Outcome-C Stage-0 reproducibility boundary is closed. Stage 0 parity is complete.**

The next governed step is the original Routed Forecast directive's candidate-alignment / pre-identifiable career-state phase. This recovery-only task stops before making a new career-state, routing-cell, cutoff, coefficient or model choice.

Execution accounting:
- Forecast model reruns: **0**
- Forecast model refits: **0**
- holdout routing runs: **0**
- current-player routing runs: **0**
- training/fold/cutoff changes: **0**
- main / PR #147 / production / Intrinsic-Shapley changes: **0**
