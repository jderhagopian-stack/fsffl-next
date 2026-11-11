# Executed 20-season hindsight Shapley replay — 2026-10-17

**Executed**, 2048 permutations per observed target season (20 distinct seasons, 2003–2022), 11,528 season-player entries, frozen marginal Shapley economic mechanism in an independently runnable local implementation, constant illustrative 12-team Superflex lineup. Every annual game is evaluated against **that target season's full observed QB/RB/WR/TE universe**. This corrects the earlier inappropriate requirement that players from a starting season must remain present in all future years.

| Starting cohort | Starter pool | Y1–Y3 continuously observed players | Y1–Y7 continuously observed | Max discounted observed Y1–Y3* | Max un-discounted observed Y1–Y7* |
|---|---:|---:|---:|---:|---:|
|2003|559|347|116|686.4155|1688.8957|
|2006|554|328|99|707.9003|1753.5575|
|2009|546|320|108|754.2188|1870.8203|
|2012|574|315|100|739.8796|1772.3315|
|2015|578|313|102|679.5049|1764.3891|

\* Maximum only among continuously *observed* athletes for each window; **selection/survivorship bias** remains. Absent seasons are explicitly `null` in individual trajectories, not imputed as zero. No terminal modeled Y8+ component; no time-appropriate forecast model; these results are **not native Career or contemporaneous 3-Year Intrinsic values**. Different scoring source and illustrative league configuration mean 754.22 does not directly reject proposed 750 for present league, nor does 1870.82 validate Career 2200.

**Important implementation caveat:** Year-wise full pool and 2048 Shapley algorithm are reproduced in a locally executed standalone replay script. Repo production implementation import/parity has NOT been certified; run unit parity before promotion. Earlier Year1 maxima differ slightly between the separate prior package and this unified replay, so investigate pool selection, row ordering and random seed/permutation order before treating exact numbers as authoritative.

## Reproducibility and durable material
- Persistent Library archive: `FSFFL_NEXT_Historical_Multiyear_Shadow_Replay_2026-10-17.zip`; Library record ID `libfile_a6babd1011608191b7bff8ef754439ce` (includes 20-year JSON player-level trajectories, runner, hashes/manifest and previous Y1 evidence). **Retrieve from Library in a new chat**, rather than assuming a local path persists.
- Original historical input: Library `player_season_panel.csv`; archive manifest has its SHA-256.
- Research PR #464, branch `research/unified-intrinsic-magnitude-shadow-20261017`.
- Continuity document: `artifacts/research/unified_intrinsic_magnitude_20261017/MANAGEMENT_CONTINUITY_HANDOFF.md`.

## Outstanding gates
1. Compare standalone Shapley implementation against actual production import on identical fixtures and verify historical pool provenance/scoring; repair any numerical drift.
2. Recover point-in-time projection model vintages or reconstruct defensible walk-forward calibration with historical cutoffs; model Y4–Y7 and Y8+ authority, age and dropout without hindsight leakage.
3. Replay 1QB versus Superflex, differing scoring and team sizes; then evaluate fixed/annual-peak/multiyear-elite anchor policy against **comparable native Career values**, with held-out seasons.
4. No live valuation change or reference approval. PR remains draft.
