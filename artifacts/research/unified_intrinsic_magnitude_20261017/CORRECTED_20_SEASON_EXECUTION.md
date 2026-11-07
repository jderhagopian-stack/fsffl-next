# Corrected 20-season hindsight Shapley replay — 2026-10-17

**Executed** locally: observed season pools 2003–2022, 2048 permutations, random seed 20260915, constant illustrative 12-team Superflex. Corrected the previously discovered RNG defect: before each `random.shuffle`, the permutation order is reset to canonical player-id ordering as in production `monte_carlo_shapley_scenarios`. The standalone basis algorithm remains a local recreation and **has not passed direct production-import numerical parity**; these remain research-only provisional hindsight outputs.

|Starting cohort|Players|Complete Y1–Y3|Complete Y1–Y7|Highest discounted observed Y1–Y3|Highest undiscounted observed Y1–Y7|
|---|---:|---:|---:|---:|---:|
|2003|559|347|116|686.8099|1689.7714|
|2006|554|328|99|705.9493|1757.4996|
|2009|546|320|108|753.6394|1876.7613|
|2012|574|315|100|740.2670|1784.8344|
|2015|578|313|102|679.4101|1762.8943|

These are observed *hindsight* Shapley marginal results. Players missing in future recorded seasons have null, NOT imputed zero. Maxima use only athletes continuously observed over corresponding horizons, creating survivorship bias. There is no point-in-time forecast model, no governed Year 8+ tail, no historical league-scoring normalization, and no native historical Career estimate. **Do not approve 750 or 2200 anchors from these figures.** The 2009 hindsight 3-year max >750 is a diagnostic, not direct proof current league reference fails.

Local corrected runner: `run_multi_year_corrected.py`; source historical panel `player_season_panel.csv`. Generated `multiyear_hindsight_shapley_corrected.json` (~1.39 MB). To reproduce with production engine: `python scripts/replay_historical_production_shapley.py player_season_panel.csv output.json --permutations 2048` in full repository environment; compare per-player annual records and identify any model mismatch.

Next acceptance: direct repo engine run, numerical parity, then historical forecast vintage / Career Y4–Y8+ reconstruction; then compare stable fixed vs annual peak vs multiyear elite cap across league formats. No production changes.
