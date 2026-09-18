# Selected Forecast Internal-Coordinate Recovery — Exact Recovery Result

Date: 2026-09-18

## Starting state verified
Research branch: a531f87a36134dc9ca3972cbc206321adb4f2ee6
Main: 53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76
PR #147: open/unmerged, head 3e63cd61602d0832acf0a30dcc5bee0b13ceeb63
Frozen Stage-C specification: 524d689bac3783c6dc31b70ce253bf0262c05e2e

No S1/S2 fitting, holdout/current-board inspection, merge, deploy, or production change.

## Recovery order executed
Existing Stage-C/B2a artifacts were inspected. They do not directly persist the required selected-Forecast player-keyed internal probability surface.

The exact historical integrated Forecast code path was recovered from research/integrated-multivariate-forecast at commit c12402df1b7fa0bfbb3d994bdcf791d80e103a0c, including run_integrated_multivariate_forecast.py, run_integrated_forecast_shapley_downstream.py, and run_persistence_first_forecast_calibration.py.

## Exact deterministic identity mapping recovered
The missing identity is not actually lost from the selected code path.

run_integrated_multivariate_forecast.py constructs each evaluation example from the canonical career panel and retains e.player_id. For each source season and horizon it evaluates the selected I1 probability surface from a source row keyed by player_id and season, with horizon h in (1,2), and calls pred(B["I1"], inp, p0).

The selected I1 probabilities are then reduced into i1_persist, i1_useful, i1_starter, and i1_premium in integrated_multivariate_oos_rows.csv. The omission of player_id from that CSV is an output-schema omission, not an absence of player identity in the selected machinery.

The downstream selected-I1 Shapley script independently proves the same contract: its forecast dictionary is keyed by (e.player_id, h) and stores the exact selected I1 probs, path, state means, and expected production before downstream Shapley calculation.

Therefore no row-order inference or cross-generation splice is required. The selected code itself supplies the deterministic player key.

## Exact probability-generation contract
At each chronological cutoff, boundaries are fitted using only data legal at that cutoff. records(...) builds training evidence with source rows satisfying x.season < cutoff and x.season+h < cutoff. fitmodel(..., arch="I1") fits the selected integrated persistence plus ordered positive-state machinery. pred(...) returns the six-state probability vector {out, depth, usable, starter, premium, elite}, normalized to one.

Selected I1 persistence equals 1-P(out). Useful, starter and premium are deterministic sums of the same state vector.

The downstream script reconstructs the selected I1 model using the frozen selected C from integrated_multivariate_forecast_results.json and stores the exact six-state vector in memory keyed by player_id and horizon.

## Important distinction
This recovery does NOT authorize silently refitting the selected model today. It proves that the exact selected player-keyed internal coordinate is reproducible from the already-frozen selected code/input/artifact contract without inventing a mapping or substituting another model generation.

The legal reusable materialization should therefore be produced by a bounded replay of the frozen selected integrated workflow that adds only player_id/source-season/horizon/fold plus the already-computed six-state probs and path to the output schema. No model, training window, C, features, state definitions, or selection may change.

## Remaining bounded execution dependency
The exact frozen authoritative workflow inputs must be replayed from their persisted artifact IDs (Model A 10318004415; QB 10317272576; disappearance 10408705946; event 10416382295; persistence 10419402765; integrated selected results 10422596781) together with frozen code commit c12402df1b7fa0bfbb3d994bdcf791d80e103a0c.

The replay must export the existing in-memory selected I1 vector with its player key and demonstrate parity to the previously frozen i1 aggregate columns.

Until that replay artifact is actually produced and parity-checked, recovery is CODE-CONTRACT PROVEN but MATERIALIZATION PENDING. S1/S2 remain stopped.

No older I1 probability artifact or persistence-first probability surface is being substituted.
