# Historical greats: observed marginal production diagnostic

Recovered `player_season_panel.csv` spans 1999–2025, 15,492 QB/RB/WR/TE player-season rows. Method: per season, replacement benchmark equals fantasy points ranked QB24 / RB30 / WR36 / TE18; sum nonnegative (player season fantasy points minus position-specific replacement season points) from selected starting season onward. Those replacement ranks are exploratory assumptions, **not replayed FSFFL league-specific Shapley/roster rules**. Therefore the calculated values must **NOT** be compared numerically to Career raw Intrinsic 2,200 or interpreted as native Shapley.

|Player|Starting year|Observed 3Y replacement-surplus points|Remaining observed replacement-surplus points|Complete?|
|---|---:|---:|---:|---|
|Peyton Manning|2003|458.6|1671.1|Yes, through 2015|
|LaDainian Tomlinson|2002|550.5|1390.6|Yes, through 2011|
|Patrick Mahomes|2018|500.2|1263.5|No; data stops 2025|
|Lamar Jackson|2019|403.2|977.7|No; data stops 2025|

Other start points: Manning 2009: 775.4 remaining observed; Tomlinson 2005: 840.1; Mahomes 2020: 950.4 (censored); Jackson 2023: 505.5 (censored).

**Result:** Preliminary historical evidence is insufficient to raise or validate a cap. Exact comparable test requires snapshot-specific league scoring, complete player and replacement pools, hindsight Y1–Y7 historical projection records versus actual outcomes, tail horizon treatment, and replaying the frozen Shapley calculation. Also independently evaluate a strictly contemporaneous (no-hindsight) projection experiment; hindsight is an upper-bound diagnostic rather than prospective proof. Keep PR research-only.
