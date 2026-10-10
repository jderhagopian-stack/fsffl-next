# Forecast/P0 dynamic input inventory — 2026-10-10

Scope: the exact source fields consumed by the accepted P0 Y2/Y3 scorer in
`src/fsffl/product/p0_forecast_runtime.py`, and the smallest safe extension of its
subject boundary. This is not a model re-fit or a change to Forecast authority.

## Input inventory

| P0 input | Frozen reference source | Dynamic source/reuse path | Availability / safeguard |
|---|---|---|---|
| Canonical player ID and position | Embedded P0 CSV and its Sleeper crosswalk | Exact `LeagueState.players` entry plus exact provider ID; candidate packet key must equal canonical State ID | Available in the preserved exact State for the 25 previously absent IDs. Name matching is not used by the new boundary. |
| Standard/non-PPR Y1 points | Frozen source coordinate; package hash `ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7` | Existing `derive_future_i1_standard_year_one(raw_forecasts, rules)` scorer | The adapter accepts only canonical player-keyed Forecast observations and uses the accepted league scoring conversion. No current candidate-keyed rows were found for the 25 subjects in `fsffl.projection_observation` through exact State as-of `2026-10-06T05:36:57.684732Z`. |
| Current source state | Frozen P0 source CSV; corrected-source builder derives it using the separately hashed position boundaries | Candidate packet must carry the state from the governed source build | The source boundaries input itself is not embedded in the runtime; only its digest is in the corrected-source manifest (`51a6a892e9a19e52b0ab8d2ac7f90b2850c199254f3021db0b5a989efdc107d5`). This tranche does not guess the boundary or substitute completed-season state for forecast-source state. |
| Age and age band | Frozen CSV; fitted P0 package | Exact State `PlayerState.age_years` at the State as-of, with age band supplied by the existing accepted feature builder | State value is usable only when present and point-in-time. The new packet validation requires a finite age. |
| Experience and career-stage route cell | Frozen CSV; accepted historical panel/entry-season derivation in corrected P0 builder | Existing NFL identity crosswalk + accepted historical panel/source derivation | Not carried by core `PlayerState`; the candidate adapter requires explicit experience and accepted career-stage output. Missing experience is not coerced to zero. |
| Prior Y1 points and coverage | Frozen CSV; accepted player-season history | Existing player-history evidence, when identity and completed-season window resolve | P0's fitted feature builder already represents unavailable prior evidence with coverage `0`; candidate rows preserve that flag/value pair. |
| Prior age/state residual and prior2 summary/coverage | Frozen CSV; accepted age/state residual history transforms | Existing history and age-completion evidence after canonical identity mapping | Optional per existing fitted missingness flags. A covered flag without its values is rejected. |
| Role, games and opportunity/game | Frozen CSV; completed player-season evidence | Existing completed-season role/opportunity facts | If not supported by evidence, existing P0 behavior uses `unknown`/zero coverage. No current-season/future values may be used. |
| Source percentile and within-state percentile | Frozen CSV, rank-derived during corrected-source build | Candidate Y1 ranked against the immutable reference coordinate; within-state rank requires accepted source-state assignment | The reference ranks can remain fixed and unchanged. Candidate state percentile cannot be computed until valid candidate Y1 and source-state inputs exist. The new API requires both. |
| League scoring multiplier | Existing `build_future_i1_player_scoring_multipliers` from candidate raw stats and league Y1 | Same existing player-specific scoring transformation | Candidate multiplier is produced only when compatible raw-stat and league-scored Y1 observations exist; no Market values or generic replacement. |

## Preserved-state evidence check

The exact 25 canonical roster IDs and exact State hash are recorded in the
CAREER_PR2_BLOCKER_HANDOFF.md committed by PR #446. Against that State's
`as_of`, a read-only query of `fsffl.projection_observation` joined to
`fsffl.projection_snapshot` returned no rows for those subjects using either
canonical `player_id` or Sleeper `external_id`, across season, rest-of-season, and
preseason snapshot horizons. The query constrained `effective_at` to the State
as-of. Thus the missing candidate Y1 is a specific input-data gap, not a failure
to reuse or execute P0's accepted scorer.

The accepted `current_i1_facts_2026` artifact was also joined by exact Sleeper
provider ID. It contains completed 2025-source-season rows for 21 of the 25
subjects. The unmatched IDs are `sleeper:player:12476`, `sleeper:player:3321`,
`sleeper:player:4018`, and `sleeper:player:4663`. Of the 21 matched rows, all 21
have a completed-season points field, 5 have prior-season points, 10 have age,
21 have an experience field, and 10 have complete role/games/opportunity
evidence. Eleven lack age in that artifact; exact State `PlayerState` age is the
point-in-time source where populated. This is useful historical evidence, not a
forecast substitute: on shared reference players, this artifact's experience is
one season behind P0's 2026 feature. The accepted entry-season/panel transform
must therefore be reused rather than copying that column directly. The artifact
does not contain P0 prior2 age/state residual transforms; those remain missing
under existing P0 coverage flags rather than being synthesized from prior points.

The accepted 335 source rows and P0 model/routes remain byte-identical. The new
runtime boundary accepts a caller-built complete candidate feature row, validates
exact State membership, position, required values, coverage/value consistency and
as-of provenance, then calls the same `_score_source` implementation. The
historical fact records above can improve prior/role coverage for 21 subjects,
but missing candidate Y1 Forecasts and the separately hashed P0 source-state
boundary mean those records do not yet form valid P0 candidate rows.

## Smallest remaining recovery action

Restore or ingest an approved, commercially permitted, point-in-time P0 input
packet for candidate IDs (standard Y1 forecast plus its accepted source-state/
percentile transform and canonical historical features). Then bind the existing
feature builders to the new candidate boundary, run the 25-ID State acceptance
population, and report each P0 forecast or per-player failure. Do not use the
research-only projection snapshots identified by PR #446, P0 model changes,
generic averages, zeroes, or Market as replacement inputs.
