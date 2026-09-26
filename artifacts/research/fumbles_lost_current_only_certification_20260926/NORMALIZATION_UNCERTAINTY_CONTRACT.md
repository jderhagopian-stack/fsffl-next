# FSFFL NEXT — Current-Only FUMBLES_LOST Normalization & Uncertainty Contract

Date: 2026-09-26 UTC  
Scope: 2026 current Forecast / Simulation only

## Design principle

The supplement must preserve three different truths:

1. **Evidence truth** — the source supplied current/rest-of-season lost-fumble evidence acquired now.
2. **Target-shape truth** — current FSFFL needs a season-equivalent rate/quantity compatible with its current season-mean scoring and weekly Simulation bridge.
3. **Historical truth** — this evidence did not exist in FSFFL before its actual acquisition time and can never be used as 2026 preseason evidence.

The existing preseason/season raw offense bundle remains byte-for-byte unchanged.

## Canonical source inputs

For each player and each accepted provider `s`:

- `F_s` = provider ROS expected lost fumbles;
- `G_s` = games represented by that ROS total when exposed;
- `captured_at_s`;
- `effective_at_s` / provider generated time when exposed;
- provider/model/source version;
- stable provider identity and canonical player mapping;
- source-health fields.

JerryGM:
- use `ros.statLine.fumblesLost`;
- use `ros.gamesRemaining`;
- require `statLineCoverage.fumblesLost == modeled`.

LineupExperts Premium:
- use ROS `ProjectedStats.FmblL`;
- record `ProjectedStats.GamesPlayed`;
- confirm in the live paid payload that the denominator describes the same ROS interval and that the row is schedule-current.

## Common target-period normalization

Do **not** add actual-to-date lost fumbles to the projection. The current Simulation bridge consumes season means as a pace and decomposes them to active-game means. The least invasive coordinate-only normalization is therefore a **17-game season-equivalent current pace**, not an expected final-season box score.

For each source:

```
canonical_remaining_games = remaining regular-season games for the player's NFL team
                            at the source acquisition cutoff

require source row to represent that current remaining window
source_rate_s = F_s / canonical_remaining_games

source_season_equivalent_s = 17 * source_rate_s
```

If a source total is documented as availability-adjusted rather than schedule-based, it may not be silently divided by a schedule denominator. Its documented denominator must be used to derive a rate with the same intended meaning or the row must be rejected. No heuristic injury adjustment is authorized.

For two accepted sources:

```
mean_fumbles_lost_current = (source_season_equivalent_A + source_season_equivalent_B) / 2
```

Equal weighting matches the existing governed independent-source baseline. No candidate-specific fitted weight is authorized.

Persist the provider ROS totals and the normalized rates separately. The season-equivalent value is a **current target-shape derivative** only.

## Non-zero uncertainty

Retained authentic 2024 pre-opener evidence provides an empirical two-source lost-fumble error study over 337 player-seasons.

At -2 fantasy points per lost fumble:
- CBS + FantasySharks equal-source RMSE = 2.2771148907 fantasy points;
- equivalent raw-event RMSE = **1.13855744535 lost fumbles**;
- mean absolute inter-source disagreement = 1.1264367816 fantasy points;
- equivalent raw-event disagreement = **0.5632183908 lost fumbles**.

For the current season-equivalent supplement:

```
x_A = source_season_equivalent_A
x_B = source_season_equivalent_B
ensemble_mean = (x_A + x_B) / 2

provider_disagreement_std = abs(x_A - x_B) / 2

empirical_coordinate_floor = 1.13855744535

supplement_stddev_events = max(
    provider_disagreement_std,
    empirical_coordinate_floor
)
```

Rationale:
- the ordinary equal-weight ensemble already represents disagreement as mixture variance;
- disagreement alone can collapse to zero;
- the retained multi-source RMSE supplies a non-zero empirical residual floor;
- using `max` avoids double-counting disagreement and historical residual error, matching the philosophy of existing season-fantasy-point uncertainty.

This is a **coordinate-specific empirical floor**, not a claim that CBS/FantasySharks calibrates JerryGM or LineupExperts individually. It is replaceable when multi-season exact PIT replay for the deployed provider pair becomes available.

At scoring time, the fumble-loss contribution to point variance is the normal coefficient transform:
`abs(fum_lost_points) * supplement_stddev_events`.

The existing broader season fantasy-point uncertainty floor still applies after scoring and uses `max`, so this coordinate floor does not replace or weaken positional forecast uncertainty.

## New persistence / authority contract

Do not write the supplement into `preseason_forecast_baseline`.

Persist a separate artifact, recommended kind:

`current_supplemental_forecast_coordinate`

Required fields:
- season = 2026;
- metric = `fumbles_lost`;
- player_id / position / NFL team;
- evidence_horizon = `rest_of_season`;
- evidence_period_start / evidence_period_end;
- source records A/B with provider, endpoint, model/source version, captured_at, effective_at, content identity/hash where rights permit, raw ROS total, source games/denominator, normalized rate, rights class and independence group;
- canonical remaining games at capture;
- target_quantity_kind = `season_equivalent_current_pace`;
- target_games = 17;
- target_mean;
- target_stddev;
- authority_valid_from;
- source-health result;
- coverage result;
- rights result;
- independence result;
- model_version.

### Authority-valid-from rule

```
authority_valid_from = max(
    source_A.captured_at,
    source_B.captured_at
)
```

The coordinate is unavailable for any evaluation cutoff earlier than `authority_valid_from`.

Hard flags:
- `preseason_eligible = false`;
- `annual_preseason_snapshot_eligible = false`;
- `historical_pit_before_authority_valid_from = false`;
- `backfill_allowed = false`.

No code path may infer an earlier effective date from provider publication history or from the 2024 replay panel.

## Runtime integration boundary

The supplement is an **overlay at current league scoring**, not a mutation of the ordinary raw Forecast.

Recommended flow:

`immutable ordinary offense raw evidence -> current-scoring overlay(FUMBLES_LOST only) -> league scoring -> season uncertainty -> current Simulation`

The scorer must accept a supplemental metric map separately from the existing observation group. It should not falsify the baseline observation's `as_of`, source, model version, or provenance merely to make grouping keys match.

For a current scored player:
- all non-fumble coordinates remain exactly those already governed;
- `FUMBLES_LOST` comes only from the accepted supplement;
- scored provenance uses the maximum retrieved/effective time across base + supplement and records both lineages;
- if the supplement is unavailable for that player, existing partial behavior remains.

The supplement may feed current Year-1 scoring/Simulation only. It is not training data, career calibration, preseason expectation, or historical replay evidence.

## Source freshness / invalidation

A persisted supplement can be reused only while:
- league season remains 2026;
- canonical player/team identity still matches;
- no accepted source has become rights-ineligible;
- the source health contract still passes;
- no completed NFL game has advanced the affected team's canonical remaining-game state beyond the evidence cutoff.

After a newly completed NFL game, the affected player's supplement row must be reacquired/recomputed before current authority is restored. Do not subtract the completed game's actual or projected fumble value from an old provider ROS row heuristically.

## Deterministic acceptance fixtures

1. Two exact current sources -> current fumble coordinate accepted.
2. One source only -> player remains partial.
3. `Fmbl` without `FmblL` -> rejected.
4. JerryGM coverage unavailable/partial -> rejected.
5. Source remaining-game state stale after a completed game -> row quarantined.
6. Different provider GP semantics -> reject unless documented denominator yields the same target-rate meaning.
7. 17-game pace normalization reproduces exact formula.
8. Equal source values still produce non-zero stddev = 1.13855744535.
9. Large provider disagreement raises stddev above the floor.
10. Pre-`authority_valid_from` evaluation cannot see the supplement.
11. Preseason baseline payload/hash is unchanged.
12. Historical/preseason comparison remains unavailable for this coordinate.
13. Changing supplement never changes pass/rush/receive observations.
14. Loss of either source demotes affected player to partial.
15. Full FSFFL Simulation promotion requires all scorer-relevant players used by current lineups to have authoritative current scoring; no missing supplement is treated as zero.
