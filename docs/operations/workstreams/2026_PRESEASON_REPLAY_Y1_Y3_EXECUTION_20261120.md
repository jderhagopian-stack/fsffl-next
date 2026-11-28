# FSFFL 2026 Preseason Model Replay — verified research results (November 20, 2026)

## Scope and historical cutoff
Exact pregame roster: September 9, 2026, 23:23:55 UTC. Opening kickoff cutoff: September 10, 2026, 00:20 UTC. Research branch and draft PR: #576. **No production promotion, no published modern-model almanac, no further hosting expense.**

The existing Sleeper transaction replayer rebuilt 238 owned player identities including **Travis Hunter on BING BONG DRIGSY (team 11)** and all 108 future draft picks. The original 2026-09-09 Analytics #65 only contained 237 of these 238: it omitted Hunter. That is an Analytics/provider normalization coverage defect, **not a transaction**. The 237 original rows match a strict subset of the reconstructed complete roster, and original starter/bench/IR/taxi placements are independently reconciled. The older pregame source required 21 completed transactions to reach 2026-09-09.

## Executed modeling
1. The accepted Simulation 2.0 model was run for 50,000 trials on the exact 238-player State (current simulation algorithm, legacy September 3 preseason forecasts). CI passed fixed-seed deterministic rerun. This is a **hybrid**, not a complete modern Forecast.
2. New script `scripts/research_2026_preseason_p0_shapley.py` actually executed unchanged accepted fitted P0 Y2/Y3 coefficients on rebuilt pregame Year-1 fantasy point inputs and adjusted pregame Y1 feature/state/rank coordinates. It then called the accepted 2,048-permutation 3-Year Shapley algorithm. **221 / 238 rostered players** received research Y1–Y3 and raw three-year Shapley; **210** reused pre-2026 reference history features and **11** used the model's documented historical-data missingness path. Missing **17** players retained explicit coverage failures—no invented zeroes or fabricated year one predictions.
3. The P0 model fit package trained on target seasons no later than 2025. Research input features `standard_y1_points`, `source_state`, `source_percentile`, `state_percentile` were **reconstructed from archived 2026 pregame projections**, not taken from the later frozen Year-1 reference board. Historical age/lag/role features came from frozen P0 rows asserted to reference completed seasons.
4. Direct source integrity audit against the user's 1999–2025 `player_season_panel.csv` (local, never uploaded to public repository): of the P0 335 reference players, **293** have a corresponding 2025 historical row, **7** are mapped to an older GSIS ID but have no 2025 row, and **35** are historical cold-starts. For all 293 mapped rows, prior1 fantasy points, games, opportunity per game and source role band matched the 2025 panel exactly (floating point tolerance). Age matched for **292/293**; Malik Davis had a one-year difference in frozen P0 age, but was **not rostered** in the September 9 research State. All 293 reference experience fields are one more than 2025 completed-season experience, consistent with projecting into 2026. This validates substantial—but not all—feature lineage.
5. The new CI workflow `research-2026-preseason-p0-shapley.yml` passed synthetic input tests and one full 2,048-permutation source-rebuilt simulation, with a compact GitHub Actions JSON artifact; `research-p0-source-history-audit.yml` independently exported original history claims for the local feature reconciliation. No private tenant payload or user Library panel was committed.

## Why this is not yet a publishable full modern-model almanac
- The September 3 licensed external Year-1 forecast is a **provisional personal-research** source; commercial/default promotion is not approved.
- The 221-player Shapley economy has **17 coverage gaps**. Marginal values and team rankings are cohort dependent; incomplete team totals must not be promoted as complete or compared unqualified.
- The relative 2026 percentile benchmark was rebuilt on the **available 221 pregame subjects**, rather than a fully verified production source universe. This is a PIT-safe **research adapter**, not a separately approved replacement production feature-selection calibration.
- The original pre-kickoff Analytics #65 contains usable fantasy-point forecasts for **six of those 17** missing-from-September-3 players (Braelon Allen, Kayshon Boutte, Marcus Mariota, Samaje Perine, Tank Dell, Jalon Daniels). They are available for a secured private exact-source bridge; this research CI does not fetch Supabase tenant rows.
- Accepted Career model additionally requires Y4–Y7 and Y8+ rebuilt using **historical point-in-time** features and the accepted Foundation4 materializer; the existing frozen 2026 long-horizon output was made later and cannot be relabeled September 9.
- Current user-facing 0–10,000 fixed magnitude calibration and future draft-pick Intrinsic require independent PIT evidence and full universe normalization. Neither was inferred from partial raw Shapley output.

## Next model implementation gates
1. Private, read-only Sept 9 original Forecast bridge to the existing source adapter; recover six additional direct pregame player projections and explicitly handle the remaining 11 without false zeroes. Keep provider permissions and licensing boundary intact.
2. Reconstruct the complete point-in-time Y1 scoring cohort and rerun accepted P0 full-cohort Y2/Y3 and Shapley with stable magnitude benchmarking. Check deterministic replay and per-player coverage.
3. Invoke accepted Foundation4 Y4–Y7 and terminal Y8+ model on *historical* source features (1999–2025), Sept 9 State, and admitted pregame Y1/Y2/Y3. Verify historical training cutoff, source licenses, and origin-age contract; do **not** reuse later 2026 frozen year-one or later-horizon source boards.
4. Assemble exact-count 3-Year and Career player values plus native pick values, rerun/playoff simulation if the new Y1 forecast changes its inputs, and freeze one immutable almanac source manifest.
5. Only after those gates promote full modeled publishing; preserve original September 9 historic predictions separately for The Receipts.

## Separate product data integrity PR
Draft **PR #578** corrects Sleeper dual-position normalization, preserving an officially declared WR-eligible/DB-primary player such as Hunter on the roster. It also fails explicitly rather than silently dropping owned players whose positions the current schema cannot represent. This is **not** a claim of complete IDP support. Exact historical root cause depends on recovery of original September 9 catalog `position`/ `fantasy_positions` values. Tests and default CI passed. No merge/deployment.

## Source identifiers
- Archived model: `fsffl.derived_artifact` id 65 (pre-kickoff), `current_forecast_evidence` id 63 (pre-kickoff).
- Frozen pregame Git source: `jderhagopian-stack/sleeper-league-data` commit `72c926cdcf9450d1ba1dcb53f67d698851b54cfb`.
- Foundation4 accepted source bundle is governed by `src/fsffl/product/foundation4_accepted_bundle.py` and `scripts/materialize_foundation4_dynamic_candidates.py`.
- Historical research runner: `scripts/research_2026_preseason_p0_shapley.py`.
- P0 / Shapley model: `p0-redeveloped-v1:ea8b5c158d6e...` and `intrinsic-shapley-i1-v1`, 2,048 permutations.

**Status:** Source-reconstructed 2026 pregame Simulation 2.0 and 221-player provisional Y1–Y3 raw Shapley completed; full model PIT Career and publishing approval **not yet completed**.
