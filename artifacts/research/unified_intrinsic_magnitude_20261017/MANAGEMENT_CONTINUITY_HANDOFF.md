## Corrected 20-season replay EXECUTED (current checkpoint)

The RNG-corrected standalone historical hindsight replay COMPLETED all 20 observed seasons 2003–2022 at 2048 permutations; prior maxima are superseded by those in `CORRECTED_20_SEASON_EXECUTION.md` (commit `e8eacc7`). Max observed discount Y1–Y3: 2003=686.8099, 2006=705.9493, 2009=753.6394, 2012=740.2670, 2015=679.4101. Max undiscounted observed Y1–Y7: 1689.7714, 1757.4996, 1876.7613, 1784.8344, 1762.8943. **Not actual prospective Career values**; still awaits direct production-engine numerical parity and time-valid forecasts plus Year8+ terminal. Full corrected raw JSON, runner, source panel, SHA256 manifest **persistently uploaded to Library** `FSFFL_NEXT_Corrected_Historical_Shapley_Replay_2026-10-17.zip`, ID `libfile_ff45fd2fe1748191ad8ea9d97c537e15`. In new conversation retrieve this latest archive instead of obsolete earlier one. Next: run `scripts/replay_historical_production_shapley.py` in actual repo Python environment at full 2048 and diff individual annual results, then model genuine forecast horizons and tail. PR remains research draft.

---

## IMPORTANT parity correction — 2026-10-17

During parity investigation discovered the archived standalone `run_multi_year_hindsight.py` executes `rng.shuffle(ids)` on an already shuffled list each permutation. Production `monte_carlo_shapley_scenarios` resets `order = player_ids[:]` before `rng.shuffle(order)` each permutation. These generate **different random permutations** even with the same seed and count. Therefore the archived 20-season maximum figures are **provisional** and MUST NOT be treated as parity-accepted or used for cap determination. The historical cohort/player-availability descriptions remain useful. Corrective implementation committed at `scripts/replay_historical_production_shapley.py`; this imports the actual production engine, uses canonical full-year pools, tracks nonappearances as null, exposes 1QB versus Superflex league-rule fixture, and holds explicit hindsight-only semantics. Test `tests/test_replay_historical_production_shapley.py`. **Run the full replay against recovered Library `player_season_panel.csv` with 2048 permutations to supersede provisional old results; record exact results, runtime and provenance.** The branch tests alone do not establish that the large replay ran. Career Y4–Y8+ forecast reconstruction still outstanding.

---

## UPDATED execution checkpoint — 20-season replay completed

Most recent research evidence: `EXECUTED_20_SEASON_SHAPLEY_HINDSIGHT.md`. The expanded observed-year full-pool hindsight Shapley replay ran **20 distinct seasons (2003–2022), 11,528 season-player entries** at 2048 permutations. Five starting cohorts have player-by-player Y1–Y8 annual observed Shapley trajectories with missing seasons shown as null, not invented zero. Reported maxima among continuously observed players: Y1–Y3 686.4/707.9/754.2/739.9/679.5 and Y1–Y7 1688.9/1753.6/1870.8/1772.3/1764.4 for 2003/06/09/12/15 respectively. These are NOT production Career estimates; no modeled Y8+ terminal nor vintage forecasts. Standalone implementation not yet parity certified; small Y1 differences with initial replay must be resolved. No cap adopted.

**Archive persisted in Library**: `FSFFL_NEXT_Historical_Multiyear_Shadow_Replay_2026-10-17.zip`, Library record `libfile_a6babd1011608191b7bff8ef754439ce` (full 1.39MB JSON, replay code, manifest/source hashes). Original `player_season_panel.csv` also remains in Library. Retrieve both by name in a NEW conversation; local `/mnt/data` paths may not persist. Source path and archive ID are provenance breadcrumbs, not license evidence. Draft PR #464 remains unmerged. Next actual implementation: parity test, walk-forward forecast construction and full Y4–Y8+ modeled Career research; do not claim a cap is selected.

---

# FSFFL NEXT — Intrinsic calibration continuity (2026-10-17)

## Where to resume
Repository: https://github.com/jderhagopian-stack/fsffl-next
Draft research PR: https://github.com/jderhagopian-stack/fsffl-next/pull/464
Branch: `research/unified-intrinsic-magnitude-shadow-20261017`
**Fetch latest PR head before continuing**; do not assume the SHA below is current.

### Product decision
3-Year = next three seasons, discounted raw Shapley; Career = remaining career, un-discounted current Y1–Y3 + long Y4–Y7 + modeled terminal Y8+. Both displayed 0–10000, linear proportional leading. Separate league-specific and horizon-specific frozen/versioned reference anchors. Proposed 750 and 2200 for current league provisional, **not approved**. Compare fixed, annual peak and historical elite reference using valid cross-season evidence; never let current top cohort or user arrival silently change scale. Broad Market is not the same unit as native Intrinsic.

### Code already in branch
`src/fsffl/product/intrinsic_magnitude_shadow.py` and `intrinsic_league_calibration.py` (shadow only); tests for magnitude curves, horizon semantics, league-rule fixture resolution. `scripts/replay_historical_shapley_hindsight.py` historical Y1 replay driver (missing Y2/Y3 coverage is explicitly gated), and `tests/test_replay_historical_shapley_hindsight.py`. See `artifacts/research/unified_intrinsic_magnitude_20261017/` for all existing gate reports, 35-player comparisons, seven Oct snapshot diagnostics, and multi-year hypothetical policies.

### Executed historical evidence (not full Career)
Recovered panel local path for original execution: `/mnt/data/files/player_season_panel.csv`; local derived paths under `/mnt/data/historical_career_replay/`. These **are not repository files**, so a fresh chat cannot assume them present; retrieve `player_season_panel.csv` from Library and regenerate under current verified source and license constraints. History 1999–2025. Five separate starting season Y1 player pools:
2003 n559 max observed Y1 Shapley 317.126;
2006 n554 max 370.767;
2009 n546 max 300.699;
2012 n574 max 287.568;
2015 n578 max 331.631.
Prior locally executed 2048-permutation replay in `historical_career_replay/run_y1.py` adapted production marginal mechanism, unverified parity with import of production module. Fixed illustrative 12-team Superflex fixture, hindsight historical fantasy outcomes (not vintage forecasts), no Y2–Y7 or Y8+ modeled tail. NEVER compare these annual values numerically to a full-Career 2200 reference. Prior tests on a later repo runner verify missingness logic, not full historical model acceptance.

### Current technical blocker
Cross-year player panel has historical nonappearances. For starting cohorts 2003/06/09/12/15, Y2 missing 133/134/135/156/163 and Y3 missing 196/210/212/238/244. Cannot silently zero-fill missing forecasts. Build each *actual observed target-year full player universe* independently to permit valid hindsight year-specific Shapley marginal diagnostics; for a given starting cohort label absent athletes as `not_observed`, never claim a production future projection. Full Career still requires time-valid forecasts, Y4–Y7 authority, Y8+ terminal and league scoring provenance. Multi-year *hindsight* results are separate diagnostics.

### Next actions
1. Version a reproducible 1999–2025 annual full-pool Shapley replay runner and provenance manifest; execute 2048 permutations on start + seven subsequent seasons using historical observations. Keep observations separate from vintage projections, coverage and censoring explicit.
2. Check numerical parity against directly imported repository `monte_carlo_shapley_scenarios` and rules `subset_caps_from_rules` using a small controlled fixture; record exact program/commit/source hash.
3. For each start-cohort report observed Y1–Y3 (where present), observed Y1–Y7 (where present), plus terminal/absence status; do **not** relabel as authoritative Career.
4. Find governed point-in-time forecast and career-tail replay recipe, and alternative league fixture packs; only then judge cap policy against actual multi-season Career Intrinsic.
5. Focused CI, update this continuity, keep draft PR unmerged and production untouched.

### Safeguards
No silent cap revision, no invented score/forecast/retirement years, no changes to production Intrinsic or broad waiver pool, never claim multi-year observed fantasy points are production Career values. Preserve all implementation/results/docs in git and source data via Library/verified downloadable artifact separately.
