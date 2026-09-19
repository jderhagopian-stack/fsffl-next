# FSFFL NEXT — Observable Collapse-Risk Stage A Reproducibility Boundary

Date: 2026-09-18

## Protected state re-fetched
- research/future-state-resolution-phase34-resume: b2cb97880694eac540bc1f8f94ea5caba5fe8608
- main: 53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76
- PR #147: open/unmerged; head 3e63cd61602d0832acf0a30dcc5bee0b13ceeb63

No protected state was modified.

## Stage A completed work
The governed collapse roster was recovered and B2a predictions were joined to the previously persisted richer-candidate rows on identical fold/horizon/source-season/player IDs.

- role-loss evaluation rows: 808
- unique player/source-season coordinates: 661
- positive R2 excess absolute error versus B2a: 11,014.069476984163 fantasy-point error units
- minimum leverage-ranked rows required to cover 50% of that positive excess: 144
- unique player IDs in that 50% sample: 99
- row mix: QB 59, RB 42, WR 41, TE 2
- source-season range: 2014–2020

This establishes the exact leverage ordering required by the directive before causal research.

## Reproducibility boundary
The durable FSFFL artifacts identify historical players by GSIS/player_id but do not contain canonical historical names. Stage A requires canonical names for all 661 unique player/source-season coordinates before Stage B.

A suitable public identity authority exists: nflverse players data, whose primary key is gsis_id and which supplies display_name. However, in this execution environment the GitHub release asset `nflverse-data/releases/download/players/players.csv` cannot be materialized into the runtime through the available connector/download path. Manual search-engine lookup can identify individual IDs, and spot checks succeeded (e.g. Nick Foles 00-0029567, Mitchell Trubisky 00-0033869, Geno Smith 00-0030565, EJ Manuel 00-0030526), but using hundreds of ad-hoc search-result matches would not satisfy the directive's requirement for a complete, reproducible identity mapping.

Therefore execution stops here rather than inventing or incompletely hand-assembling the 661-name mapping.

## What has NOT occurred
- Stage B causal classifications have not begun.
- No non-collapse control analysis has been performed.
- Stage C feature eligibility has not been evaluated.
- No S1/S2 candidate has been fit.
- No 2021–2022 selection use.
- No current-board selection/tuning.
- No model/production/PR/main/Shapley changes.

## Dependency needed to resume
Materialize a versioned/captured GSIS-to-display-name identity snapshot covering the 661 IDs (the nflverse players.csv release is sufficient if its bytes can be retrieved and hashed). Once available, Stage A can be completed deterministically and Stage B can proceed leverage-first as specified.
