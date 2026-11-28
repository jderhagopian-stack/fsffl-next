"""Bounded historical Year-1 -> accepted P0 Y2/Y3 -> Shapley research backcast.

This is NOT a published 3-Year/Career Intrinsic result. Unlike the current
2026 live player board, the Y1 and its model-input percentiles/state are
recomputed from the preserved Sept-3/Sept-9 preseason evidence. The P0 fitted
coefficients and Shapley algorithm are unchanged. The model's 2025 historical
feature columns are reused from the frozen reference, while nonreference
subjects use the model's explicit history-missingness features.

Crucial limitations:
* External Sept-3 Y1 projections are personal research licensed only.
* Some rostered players lack preseason projections. They are NOT set to zero.
* The 335-player model benchmark is reconstructed only for the eligible
  preseason forecast cohort, not frozen/certified as a replacement production
  calibration. Shapley therefore depends on the covered player universe.
* This calculates Y1-Y3 research. It does not invent Career Y4+ or a 0-10000
  display calibration.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
import argparse
import json
import math
from pathlib import Path

from fsffl.product.p0_forecast_runtime import (
    P0SourceRow, P0_FORECAST_VERSION, _score_source, frozen_p0_source_rows,
)
from fsffl.product.p0_candidate_evidence import (
    _current_state, _benchmark_percentile, accepted_p0_source_state_authority,
)
from fsffl.product.i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING
from fsffl.product.i1_player_scoring import (
    player_scoring_multipliers, translate_future_i1_result_for_player,
)
from fsffl.value.live_intrinsic_calendar import (
    compose_live_intrinsic_calendar_from_future_results,
    build_live_calendar_shapley_estimates,
)

try:
    from scripts.research_frozen_2026_hybrid_simulation import (
        ARCHIVE_CAPTURE, assemble_vintage_state_and_forecasts, load_pinned_sources,
    )
    from scripts.research_2026_sept9_reconstruction import AS_OF, reconstruct_sept9_sources
except ModuleNotFoundError:
    from research_frozen_2026_hybrid_simulation import (
        ARCHIVE_CAPTURE, assemble_vintage_state_and_forecasts, load_pinned_sources,
    )
    from research_2026_sept9_reconstruction import AS_OF, reconstruct_sept9_sources


RESEARCH_VERSION = "2026-sept9-p0-y2y3-shapley-preseason-inputs-research-v1"
SCORING_METRICS = frozenset(rule.stat for rule in FROZEN_I1_STANDARD_SCORING)


def _standard_y1(row: dict) -> float:
    stats = row.get("projected_stats")
    if not isinstance(stats, dict):
        raise ValueError("preseason player lacks full projected-stat evidence")
    if "fum_lost" not in stats:
        raise ValueError("preseason scoring lacks lost-fumbles observation")
    result = 0.0
    for rule in FROZEN_I1_STANDARD_SCORING:
        value = stats.get(rule.stat)
        if value is None:
            # The source has position-specific stat schemas: a WR without a
            # pass_yd field has no passing projection. This is not an invented
            # 0 for a wholly absent player.
            value = 0.0
        if not math.isfinite(float(value)):
            raise ValueError(f"non-finite raw preseason stat {rule.stat}")
        result += float(value) * float(rule.points)
    return result


def _source_age_and_experience(player, state, raw):
    current = next((x for x in state.player_states if x.player_id == player.player_id), None)
    if current is None or current.age_years is None:
        raise ValueError("candidate has no preseason State age evidence")
    yrs = raw.get("years_exp")
    if yrs is None:
        raise ValueError("candidate lacks preseason NFL experience evidence")
    # P0 empirical source rows are indexed to the last completed 2025 season,
    # while old Sleeper catalog reports values at the start of 2026.
    return max(0.0, float(current.age_years) - 1), max(0, int(yrs) - 1)


def _candidate_row(pid, player, state, raw, *, standard, league, source_state, pos_pct, state_pct):
    age, experience = _source_age_and_experience(player, state, raw)
    stage = "developmental" if experience <= 3 else ("established" if experience <= 8 else "veteran")
    band = "young" if age <= (25 if player.position.value == "QB" else 22) else (
        "prime" if age <= (31 if player.position.value == "QB" else 27) else "aging"
    )
    input_sha = sha256(json.dumps({
        "source_era": ARCHIVE_CAPTURE.isoformat(), "id": pid, "age": age,
        "experience": experience, "standard_y1": standard, "league_y1": league,
    }, sort_keys=True).encode()).hexdigest()
    # Legitimate P0 missingness path: previous-season production was not
    # collected for this nonreference subject by the frozen source pack.
    return P0SourceRow(
        player_id=pid, current_player_id=pid,
        player_name=player.full_name, position=player.position.value,
        age=age, experience=experience,
        career_stage=stage, age_band=band,
        mapping_status="NONREFERENCE_HISTORICAL_MISSINGNESS",
        historical_gsis_id=None,
        history_status="PRIOR_HISTORY_NOT_AVAILABLE_TO_THIS_BOUNDED_REPLAY",
        standard_y1_points=standard, connected_league_y1_points=league,
        source_state=source_state, prior1_points=None, prior1_coverage=0,
        source_role_band="unknown", games=None, opportunity_per_game=None,
        prior_age_state_resid_z=None, prior2_coverage=0,
        prior2_mean_age_state_z=None, prior2_gap_age_state_z=None,
        source_percentile=pos_pct, state_percentile=state_pct,
        evidence_as_of=AS_OF.isoformat(), evidence_source_version=RESEARCH_VERSION,
        evidence_sha256=input_sha,
    )


def build_pregame_p0_research(*, permutations: int = 2048) -> dict:
    if not 32 <= permutations <= 2048:
        raise ValueError("research permutations must be bounded to 32..2048")
    raw = load_pinned_sources()
    reconstructed, receipt = reconstruct_sept9_sources(raw)
    state, y1_source, source_coverage = assemble_vintage_state_and_forecasts(
        reconstructed, state_as_of=AS_OF
    )
    if len(state.teams) != 12 or sum(len(x.roster) for x in state.team_states) != 238:
        raise ValueError("complete 238-member historical State was not preserved")
    references = {x.player_id: x for x in frozen_p0_source_rows()}
    if len(references) != 335:
        raise ValueError("original fitted P0 335 reference changed")
    rostered = {p.player_id: x.team_id for x in state.team_states for p in x.roster}
    canonical = {p.player_id: p for p in state.players}
    old_catalog = reconstructed["data/players.json"]
    legacy = reconstructed["data/simulator/2026/sources/preseason_fsffl_points.json"]["players"]
    original_observations = {p.player_id: p for p in y1_source}
    authority = accepted_p0_source_state_authority()

    candidates = {}
    missing = []
    for pid in sorted(rostered):
        player = canonical.get(pid)
        old = legacy.get(pid.rsplit(":", 1)[-1])
        observation = original_observations.get(pid)
        if player is None or player.position.value not in {"QB", "RB", "WR", "TE"}:
            missing.append({"player_id": pid, "reason": "missing canonical offensive identity"})
            continue
        if not isinstance(old, dict) or observation is None:
            missing.append({"player_id": pid, "name": player.full_name,
                            "reason": "pre-kickoff season Forecast absent; not imputed"})
            continue
        try:
            standard = _standard_y1(old)
        except (ValueError, TypeError) as exc:
            missing.append({"player_id": pid, "name": player.full_name,
                            "reason": str(exc)})
            continue
        league = float(observation.distribution.mean)
        if not math.isfinite(league) or league < 0 or standard < 0:
            missing.append({"player_id": pid, "name": player.full_name,
                            "reason": "unusable preseason scoring coordinate"})
            continue
        # Player ratio is accepted only when the standard coordinate is positive
        # or both coordinates are zero; do not invent a ratio for missing stats.
        if standard == 0 and league > 0:
            missing.append({"player_id": pid, "name": player.full_name,
                            "reason": "nonzero league points with zero standard points"})
            continue
        candidates[pid] = {
            "player": player, "observation": observation,
            "standard": standard, "league": league,
        }
    if not candidates:
        raise ValueError("no qualified historical fantasy-point Forecast inputs")
    pos_values = defaultdict(list)
    for row in candidates.values():
        pos_values[row["player"].position.value].append(row["standard"])
    for row in candidates.values():
        pos = row["player"].position.value
        row["source_state"] = _current_state(
            row["standard"], authority.thresholds_by_position[pos]
        )
    by_cell = defaultdict(list)
    for row in candidates.values():
        by_cell[(row["player"].position.value, row["source_state"])].append(row["standard"])

    standard_y1, league_y1, future = [], [], {}
    model_sources = {}
    for pid, row in sorted(candidates.items()):
        player, standard, league = row["player"], row["standard"], row["league"]
        pos, cell = player.position.value, row["source_state"]
        pct = _benchmark_percentile(standard, pos_values[pos])
        state_pct = _benchmark_percentile(standard, by_cell[(pos, cell)])
        ref = references.get(pid)
        if ref is not None:
            # The accepted P0 coefficients & 2025 history features are reused.
            # Never use the later 2026 frozen board's Y1, source_state or rank.
            source = replace(ref,
                standard_y1_points=standard, connected_league_y1_points=league,
                source_state=cell, source_percentile=pct,
                state_percentile=state_pct,
            )
            model_sources[pid] = "reference_2025_history_rebuilt_2026_y1"
        else:
            raw_player = old_catalog.get(pid.rsplit(":", 1)[-1], {})
            try:
                source = _candidate_row(pid, player, state, raw_player,
                    standard=standard, league=league, source_state=cell,
                    pos_pct=pct, state_pct=state_pct)
            except (ValueError, TypeError) as exc:
                missing.append({"player_id": pid, "name": player.full_name,
                                "reason": str(exc)})
                continue
            model_sources[pid] = "candidate_preseason_missing_history"
        obs = row["observation"]
        league_y1.append(obs)
        standard_y1.append(obs.model_copy(update={
            "distribution": obs.distribution.model_copy(update={"mean": standard}),
            "source": "fsffl:preseason_baseline:2026-sept3-standard",
            "model_version": RESEARCH_VERSION + ":standard",
        }))
        future[pid] = _score_source(source, player_id=pid,
            standard_y1_points=standard)

    multiples = player_scoring_multipliers(
        standard_year_one=tuple(standard_y1), league_year_one=tuple(league_y1)
    )
    by_horizon = {
        pid: {
            h: translate_future_i1_result_for_player(
                pid, scored.result_for(h), multipliers=multiples
            ) for h in (2, 3)
        }
        for pid, scored in future.items()
    }
    calendar = compose_live_intrinsic_calendar_from_future_results(
        live_year_one_forecasts=tuple(league_y1),
        future_results=by_horizon, future_source_season=2026,
    )
    shapley = build_live_calendar_shapley_estimates(
        calendar, rules=state.league.rules, permutations=permutations
    )
    estimates = {x.player_id: x for x in shapley.estimates}
    player_results = []
    for pid, row in sorted(candidates.items()):
        if pid not in estimates:
            continue
        value = estimates[pid]
        futures = by_horizon[pid]
        player_results.append({
            "player_id": pid, "team_id": rostered[pid],
            "player_name": row["player"].full_name,
            "position": row["player"].position.value,
            "source_class": model_sources[pid],
            "year_1_points": round(row["league"], 4),
            "year_2_expected_points": round(futures[2].anticipated_points, 4),
            "year_3_expected_points": round(futures[3].anticipated_points, 4),
            "three_year_raw_shapley": round(value.value, 6),
            "year_1_shapley": round(value.year_1_shapley, 6),
            "year_2_shapley": round(value.year_2_expected_shapley, 6),
            "year_3_shapley": round(value.year_3_expected_shapley, 6),
        })
    player_results.sort(key=lambda x: -x["three_year_raw_shapley"])
    team_totals = defaultdict(float)
    team_counts = defaultdict(int)
    for item in player_results:
        team_totals[item["team_id"]] += item["three_year_raw_shapley"]
        team_counts[item["team_id"]] += 1
    return {
        "status": "provisional_historical_preseason_p0_y2y3_shapley_research",
        "publication_ready": False,
        "source_as_of": AS_OF.isoformat(),
        "preseason_forecast_as_of": ARCHIVE_CAPTURE.isoformat(),
        "model_version": P0_FORECAST_VERSION,
        "feature_adapter_version": RESEARCH_VERSION,
        "permutations": permutations,
        "coverage": {
            "rostered": len(rostered),
            "preseason_y1_model_qualified": len(player_results),
            "missing": sorted(missing, key=lambda x:x["player_id"]),
            "reference_cohort": sum(v.startswith("reference") for v in model_sources.values()),
            "candidate_with_history_missingness": sum(v.startswith("candidate") for v in model_sources.values()),
            "shapley_player_cohort_is_incomplete": len(player_results) != len(rostered),
        },
        "team_raw_shapley_totals_incomplete": [
            {"team_id": team, "covered_players": team_counts[team],
             "partial_three_year_raw_shapley": round(total, 6)}
            for team, total in sorted(team_totals.items(), key=lambda x:-x[1])
        ],
        "player_results": player_results,
        "limits": [
            "Only Y1-Y3 covered; no Career Y4-Y7, Y8 tail, or pick Intrinsic computed",
            "Source-era original external preseason player projections are personal research only",
            "Frozen model trained on <=2025 but features rebuilt from 2026 vintage",
            "Reference source age/2025 history retained; candidate history unavailable",
            "Input benchmark percentiles are inferred from coverage-limited preseason sample",
            "Missing players not assigned zero; Shapley depends on incomplete covered cohort",
            "Raw Shapley output, not the magnitude-calibrated 0-10,000 user display scale",
        ],
        "reconstruction": {
            "transaction_count": receipt["transactions_applied"],
            "roster_count": receipt["complete_roster_member_count"],
            "draft_pick_count": receipt["source_frozen_pick_count"],
            "hunter_preserved": any(x.get("player_id")=="sleeper:player:12530"
                                  for x in receipt["archived_analytics_coverage_defects"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--permutations", type=int, default=2048)
    args = parser.parse_args()
    result = build_pregame_p0_research(permutations=args.permutations)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n")
    print("PRESEASON_P0_THREE_YEAR_RESEARCH_COMPLETED")
    print("COVERAGE",result["coverage"]["preseason_y1_model_qualified"],
          "/",result["coverage"]["rostered"])
    print("P0",result["model_version"],"permutations",result["permutations"])
    for i,row in enumerate(result["team_raw_shapley_totals_incomplete"],1):
        print(i,row["team_id"],row["covered_players"],
              row["partial_three_year_raw_shapley"])


if __name__ == "__main__":
    main()
