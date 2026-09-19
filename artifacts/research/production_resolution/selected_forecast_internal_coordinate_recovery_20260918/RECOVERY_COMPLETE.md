# Selected Forecast Internal Coordinate — Recovery Complete

Date: 2026-09-18

The recovery-only directive is satisfied.

## Exact recovered materialization
Workflow run: 35407584656
Artifact: 10572329012
File: selected_forecast_internal_probabilities.csv
Rows: 12,920
Unique (player_id, source_season, horizon) keys: 12,920
Source seasons: 2005–2020
Horizons: 1 and 2
SHA-256: 41593ad6a90e3fcb76704d72e57e76b8b4b0b6e377bdcf05ed1df16e05f86244

Schema includes player_id, source_season, horizon, position, selected route/path, six-state probabilities (out/depth/usable/starter/premium/elite), and deterministic persistence/useful/starter/premium aggregates.

## Provenance
Selected code commit: c12402df1b7fa0bfbb3d994bdcf791d80e103a0c
Selected architecture: I1
Selected C: 0.25
Frozen input artifact IDs: 10318004415, 10317272576, 10408705946, 10416382295, 10419402765, 10422596781.

The replay checked out the frozen selected code commit, rebuilt the governed PIT career/usage panels through the original extraction scripts, downloaded the exact frozen authoritative artifacts, verified the original baseline parity assertions, and replayed the selected I1 code path. It did not select or tune a model.

## Identity / probability proof
The selected code path itself carries e.player_id through each chronological evaluation example and computes the selected I1 vector for each (player_id, source_season, horizon). No row-order identity inference was used. No older I1 or persistence-first probability surface was substituted.

The materialization has zero duplicate keys. Every six-state vector sums to one within floating-point tolerance (observed maximum absolute sum error 6.66e-16).

The selected aggregate coordinates are deterministically reconstructed from the vector:
persist = 1-P(out)
useful = sum(usable, starter, premium, elite)
starter = sum(starter, premium, elite)
premium = sum(premium, elite)

## Governance
No holdout seasons 2021–2022 were materialized or inspected. No current-player board was used. No S1/S2 fitting occurred. No main, PR #147, B2a, production, Intrinsic/Shapley, C=0.25, or 0.85-discount change occurred.

## Next boundary
The exact player-keyed selected-Forecast internal coordinate required for legal Stage-C attachment now exists. Stage C may resume from the already-frozen specification at commit 524d689bac3783c6dc31b70ce253bf0262c05e2e without reopening feature selection.

This recovery task stops here, before S1/S2.
