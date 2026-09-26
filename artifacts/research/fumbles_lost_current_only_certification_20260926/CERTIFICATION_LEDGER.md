# FSFFL NEXT — Current-Only FUMBLES_LOST Certification Ledger

Date: 2026-09-26 UTC  
Workstream: Forecast Research  
Scope: 2026 current-intelligence supplemental coordinate only

## Governing boundary

This package implements the Management correction in `docs/operations/workstreams/RESEARCH.md`.

It does **not** rebase or replace any unrelated QB/RB/WR/TE Forecast coordinate. The existing retained offense evidence remains authoritative for every currently governed coordinate except that current scoring may consume a separately governed `FUMBLES_LOST` supplement when and only when this supplement passes its own authority gate.

`FUMBLES_LOST` remains core/material. Two independent sources are required.

## Shortest source path

### Candidate A — JerryGM Projections API

**Technical fit: GREEN / live authenticated payload not yet acquired**

Public v1 documentation proves:
- exact native `statLine.fumblesLost`;
- `week=current&horizon=ros`;
- a `ros` block with schedule-based `gamesRemaining` and `ros.statLine` totals;
- `generatedAt`, `dataThroughWeek`, and per-component `statLineCoverage`;
- current season 2026 support;
- stable Sleeper/GSIS crosswalk IDs;
- provider-owned projection model output derived from nflverse.

Source:
- https://api.jerrygm.com/api/ext/v1/docs
- https://www.jerrygm.com/api/
- https://www.jerrygm.com/terms/

Required source-health checks on an authenticated capture:
1. season = 2026;
2. week alias resolves to canonical current/upcoming week;
3. horizon = ROS;
4. `generatedAt <= captured_at`;
5. `dataThroughWeek` is not ahead of canonical completed NFL state;
6. `statLineCoverage.fumblesLost == modeled`;
7. each accepted row has non-null team, stable ID, positive schedule `gamesRemaining`, and finite non-negative `ros.statLine.fumblesLost`;
8. provider `gamesRemaining` matches canonical team remaining games at capture;
9. no row is silently accepted when coverage says unavailable/partial without an explicit governed decision.

**Independence: GREEN at provider-model level.** JerryGM states this is its own projection model. One JerryGM source/model family counts as one provider vote regardless of internal variants.

**Private-beta rights: REVIEW_REQUIRED.** Current terms license API output for use within the user's own applications and explicitly contemplate derived displayed numbers with attribution on Free/Starter, but they prohibit use to train or calibrate a competing projection product and prohibit presenting output as one's own model. Existing FSFFL source governance therefore requires written clarification that the narrow use below is permitted:
- ingest only the exact current `fumblesLost` coordinate plus required provenance;
- combine it with one independent provider under FSFFL's governed equal-weight supplement;
- do not use JerryGM output to train or calibrate FSFFL coefficients;
- preserve JerryGM provenance/attribution where required;
- do not redistribute the raw feed.

No JerryGM production authority is promoted by this Research artifact.

### Candidate B — LineupExperts Premium In-Season Projections

**Technical fit: GREEN for coordinate/schema + public ROS product; live paid ROS payload not yet acquired**

Public evidence now proves materially more than the prior checkpoint:
- the Premium In-Season demo emits both total fumbles `Fmbl` and exact lost fumbles `FmblL`;
- the Premium In-Season product supports the same intervals as standard In-Season, explicitly including rest-of-season;
- public 2026 ROS boards are live and populate hundreds of players;
- the public ROS board exposes projected games, allowing schedule-freshness checks;
- current public rows are schedule-aware after the Thursday 2026-09-24 game (Atlanta examples show 14 projected games remaining while teams that had not yet played show 15).

Sources:
- https://www.lineupexperts.com/API-Football-Reference
- https://api.lineupexperts.com/v1demo/nfl-ProjectionsInSeasonPremium?key=abc123&interval=current_week
- https://www.lineupexperts.com/API-Pricing
- https://www.lineupexperts.com/football/projections?flt_proj_time_period=RestOfSeason
- https://www.lineupexperts.com/terms.php

The Premium demo returns, for example, `FmblL: 0.2` for Josh Allen and Jacoby Brissett and explicit `0.0` for other rows. This proves the field is distinct from total fumbles.

Required source-health checks on a paid ROS capture:
1. interval is the provider's documented rest-of-season interval;
2. row contains `FmblL` and `GamesPlayed`;
3. field values are finite/non-negative;
4. provider projected games are consistent with canonical remaining schedule semantics;
5. no already-completed game is still included in the row;
6. all target QB/RB/WR/TE rows are returned by the live endpoint rather than the demo subset;
7. player identity resolves uniquely into the canonical Sleeper player universe.

**Independence: REVIEW_REQUIRED, strong direct-provider candidate.** LineupExperts repeatedly describes the projection product as “our projections” / “our system,” and the Premium projection endpoint is a LineupExperts product rather than an explicitly identified consensus feed. However its API terms also say some API content may come from third parties. Before this endpoint counts as the second independent projection vote, obtain written confirmation that the Premium NFL projection values, specifically `FmblL`, are LineupExperts-generated projection output and do not embed JerryGM or another provider being counted separately.

**Private-beta rights: REVIEW_REQUIRED.** API terms permit subscribed API use in declared web sites/applications/forums and prohibit resale/sublicensing, benchmarking/competitive monitoring, and use outside declared forums. They do not clearly grant the specific persisted-derived-model-input pattern FSFFL requires. Obtain written confirmation that the declared private-beta FSFFL application may:
- ingest `FmblL` from Premium In-Season ROS;
- retain the minimal value/provenance needed for current Forecast reproducibility;
- combine it with one independent projection source into a derived current supplement;
- expose only derived FSFFL outputs, not the raw feed.

### Why this pair is shortest

**JerryGM + LineupExperts Premium** is the shortest technical two-source path now found because:
- both expose the exact lost-fumble coordinate;
- both support current/in-season ROS evidence;
- both are direct projection-product candidates rather than known consensus aggregators;
- both expose or can expose schedule/period information needed to normalize to a common target;
- both have practical API product paths.

The remaining red gates are external rights/account/live-capture gates, not missing coordinate semantics.

## Alternatives exhausted

### Fantasy Nerds

Technically exact `fumbles_lost` and an ROS endpoint exist, and paid API use has a plausible application-use path. It is not the preferred second vote because Fantasy Nerds describes its projection product as a weighted multi-site consensus. Without source decomposition it cannot satisfy the two-independent-source rule against a named direct source.

### SportsDataIO

Strong clean fallback:
- player projection schemas contain exact `FumblesLost`;
- SportsDataIO markets partial-season / ROS projections;
- provider projections are available through SportsDataIO's own projection products/models;
- commercial licenses can explicitly permit storage plus use as input to models/analytics.

But Discovery Lab is personal/non-commercial only and a hosted FSFFL beta cannot assume it qualifies. A suitable commercial/model-input license therefore remains an external dependency. This makes SportsDataIO a cleaner contractual fallback if licensed, but not the shortest current self-serve path.

### Razzball

Current ROS position pages expose lost fumbles but previously failed current source-health semantics and require explicit consent for model/aggregation use. The season source intentionally removed cross-horizon fumble augmentation. Not a certification path.

### CBS / FantasySharks retained 2024

Authentic exact PIT evidence remains useful for replay/uncertainty only. It is the wrong current season/cutoff and does not create 2026 deployment rights.

## Coverage requirement

Certification is **per player × metric × current supplement cutoff**.

Full current player-offense scoring may be promoted only when every player in the governed current QB/RB/WR/TE Forecast universe that requires `fum_lost` scoring has:
- a valid canonical identity;
- one accepted JerryGM value;
- one accepted LineupExperts value;
- the same normalized target-period identity;
- no source-health or rights blocker.

A global provider row count is diagnostic, not authority. Any undercovered player remains partial; absent/missing is never zero.

## Current live-evidence status

What is already publicly verifiable:
- JerryGM schema/ROS semantics/health metadata/exact field: **GREEN**;
- LineupExperts exact Premium `FmblL` schema: **GREEN**;
- LineupExperts current ROS product/population and schedule freshness: **GREEN**;
- direct API products exist for both: **GREEN**.

What cannot be validated without external account/rights evidence:
- authenticated JerryGM current ROS full-pool payload and canonical-player coverage;
- paid LineupExperts Premium current ROS full-pool payload and canonical-player coverage;
- written JerryGM narrow derived-ensemble permission;
- written LineupExperts model-input/persistence permission;
- written LineupExperts endpoint-ownership/independence confirmation.

Those are the exact remaining certification dependencies.
