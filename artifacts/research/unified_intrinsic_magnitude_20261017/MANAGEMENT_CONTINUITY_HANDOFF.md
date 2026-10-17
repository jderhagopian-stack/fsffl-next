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
