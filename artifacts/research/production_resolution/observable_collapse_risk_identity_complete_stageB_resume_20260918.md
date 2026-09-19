# Observable Collapse-Risk — Identity Materialization Complete / Stage B Resumed

Date: 2026-09-18

## Identity dependency resolved
A deterministic nflverse player registry snapshot was materialized by GitHub Actions from:
https://github.com/nflverse/nflverse-data/releases/download/players/players.csv

Retrieval UTC: 2026-09-18T23:01:07.747710+00:00
SHA-256: 801d5fec2fc21c54ad585415e8e551ae9d1de7c601a8c3768504b7ce59b579b6
Bytes: 7,259,734
Registry rows: 24,706
Primary key: gsis_id

All 398 distinct GSIS IDs represented by the 661 collapse player/source-season coordinates resolved deterministically to canonical names. Unresolved IDs: 0.

The archived nflverse-data snapshot dated 2026-09-17 independently records players.rds SHA-256 9eff1776e16e045e803ecba725c54d2ab0faec450a081747ed507dc85e9fd2c5, establishing a versioned adjacent archive coordinate for the player registry.

## Stage A
The previously frozen leverage ordering was not recomputed or altered. The 50% leverage sample remains 144 observations / 99 unique players.

## Stage B status
Stage B has resumed. Contemporaneous public evidence is being evaluated against the explicit source-season-completion cutoff. Initial high-leverage checks already demonstrate both kinds of cases:
- observable structural warnings (for example EJ Manuel had already been benched for Kyle Orton during the 2014 source season);
- later events that must not be backfilled as source-time warnings (for example Case Keenum's March 2019 Denver trade occurs after the 2018 source-season cutoff).

A reproducible roster-status/control extraction has been launched on the research branch using nflverse weekly-roster data and the frozen Phase-2 artifact. No model fitting is authorized until causal reconstruction, controls, and the Stage C eligibility gate are complete.

No main/PR147/production/Shapley changes.
