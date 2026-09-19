from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import UTC, datetime
from pathlib import Path

from fsffl.forecast.i1_artifact import FrozenI1Artifact
from fsffl.forecast.i1_current_facts import CurrentI1FactsArtifact, map_current_i1_facts
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.i1_scoring_bridge import (
    FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION,
    LeagueScoringNormalizedI1Predictor,
    position_scoring_multipliers,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    ProviderRef,
    Team,
    TeamState,
)
from fsffl.value.live_intrinsic_calendar import (
    build_live_calendar_shapley_estimates,
    compose_live_intrinsic_calendar,
)
from fsffl.value.private_beta_activation_data import activation_artifact_text
from fsffl.value.shapley_intrinsic import FROZEN_SHAPLEY_PERMUTATIONS


EXPECTED_MULTIPLIERS = {
    Position.QB: 1.04575952979839,
    Position.RB: 1.11430683937932,
    Position.WR: 1.2899047488253,
    Position.TE: 1.35877076106381,
}
BASE_SENTINELS = (
    "Josh Allen",
    "Bijan Robinson",
    "Jahmyr Gibbs",
    "Christian McCaffrey",
    "Puka Nacua",
    "Sam Darnold",
    "Aaron Rodgers",
)


def _load(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return raw


def _provider_external_id(player_id: str) -> str:
    prefix = "sleeper:player:"
    if not player_id.startswith(prefix):
        raise ValueError(f"unexpected canonical player id: {player_id}")
    value = player_id[len(prefix):]
    if not value:
        raise ValueError(f"empty Sleeper id: {player_id}")
    return value


def _league_state(rows: list[dict], rules: LeagueRules, as_of: datetime) -> LeagueState:
    league_id = "sleeper:1312071960615731200"
    provenance = Provenance(
        source="credibility-gate:recovered-preseason-coordinate",
        retrieved_at=as_of,
        effective_at=as_of,
        source_version="credibility-gate-v1",
    )
    players = tuple(
        Player(
            player_id=str(row["player_id"]),
            full_name=str(row["full_name"]),
            position=Position(str(row["position"])),
            provider_refs=(
                ProviderRef(
                    provider="sleeper",
                    external_id=_provider_external_id(str(row["player_id"])),
                ),
            ),
        )
        for row in rows
    )
    teams = tuple(
        Team(team_id=f"diagnostic-team-{index}", league_id=league_id, display_name=f"Diagnostic {index}")
        for index in range(1, rules.team_count + 1)
    )
    return LeagueState(
        league=League(
            league_id=league_id,
            name="FSFFL NEXT credibility gate",
            season=2026,
            rules=rules,
        ),
        as_of=as_of,
        teams=teams,
        team_states=tuple(TeamState(team_id=team.team_id, roster=()) for team in teams),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=as_of,
                nfl_team=player.nfl_team,
                provenance=provenance,
            )
            for player in players
        ),
    )


def _obs(row: dict, *, source: str, model_version: str, stddev: float) -> ForecastObservation:
    as_of = datetime.fromisoformat(str(row["as_of"]).replace("Z", "+00:00")).astimezone(UTC)
    return ForecastObservation(
        player_id=str(row["player_id"]),
        position=Position(str(row["position"])),
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 1, 1, tzinfo=UTC),
        period_end=datetime(2027, 1, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=float(row["mean"]), stddev=float(stddev)),
        source=source,
        model_version=model_version,
        as_of=as_of,
        provenance=Provenance(
            source=source,
            retrieved_at=as_of,
            effective_at=as_of,
            source_version=model_version,
        ),
    )


def _finite_nonnegative(*values: float) -> bool:
    return all(math.isfinite(float(value)) and float(value) >= 0.0 for value in values)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league-board", type=Path, required=True)
    parser.add_argument("--standard-board", type=Path, required=True)
    parser.add_argument("--league-rules", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    league_payload = _load(args.league_board)
    standard_payload = _load(args.standard_board)
    rules = LeagueRules.model_validate(_load(args.league_rules))
    league_rows = list(league_payload["rows"])
    standard_rows = list(standard_payload["rows"])

    if len(league_rows) != 335 or len({row["player_id"] for row in league_rows}) != 335:
        raise RuntimeError("league Year-1 board is not the recovered 335-player coordinate")
    if len(standard_rows) != 335 or len({row["player_id"] for row in standard_rows}) != 335:
        raise RuntimeError("standard Year-1 board is not the recovered 335-player coordinate")
    if {row["player_id"] for row in league_rows} != {row["player_id"] for row in standard_rows}:
        raise RuntimeError("standard and league Year-1 coordinates do not have identity parity")

    as_of = datetime.fromisoformat(str(league_payload["evaluation_as_of"]).replace("Z", "+00:00")).astimezone(UTC)
    state = _league_state(league_rows, rules, as_of)

    league_year_one = tuple(
        _obs(
            row,
            source="fsffl:preseason_baseline_league_scored",
            model_version=str(row["model_version"]),
            stddev=float(row["stddev"]),
        )
        for row in league_rows
    )
    standard_year_one = tuple(
        _obs(
            row,
            source="fsffl:i1_frozen_standard_scoring",
            model_version=FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION,
            stddev=0.0,
        )
        for row in standard_rows
    )
    multipliers = position_scoring_multipliers(
        standard_year_one=standard_year_one,
        league_year_one=league_year_one,
    )
    for position, expected in EXPECTED_MULTIPLIERS.items():
        actual = multipliers.get(position)
        if actual is None or abs(actual - expected) > 1e-12:
            raise RuntimeError(
                f"scoring multiplier drift for {position.value}: actual={actual} expected={expected}"
            )

    facts = CurrentI1FactsArtifact.from_dict(
        json.loads(activation_artifact_text("current_i1_facts_2026.json"))
    )
    h12 = FrozenI1Artifact.from_dict(
        json.loads(activation_artifact_text("frozen_i1_h12.json"))
    )
    h3 = FrozenI1Artifact.from_dict(
        json.loads(activation_artifact_text("frozen_i1_h3.json"))
    )
    mapping = map_current_i1_facts(state, facts)
    if mapping.unmapped_player_ids or mapping.ambiguous_player_ids:
        raise RuntimeError(
            "credibility gate requires complete current-fact mapping; "
            f"unmapped={mapping.unmapped_player_ids}; ambiguous={mapping.ambiguous_player_ids}"
        )
    if mapping.mapped_count != 335:
        raise RuntimeError(f"credibility gate mapped {mapping.mapped_count}/335 players")

    near = LeagueScoringNormalizedI1Predictor(h12, multipliers=multipliers)
    far = LeagueScoringNormalizedI1Predictor(h3, multipliers=multipliers)
    calendar = compose_live_intrinsic_calendar(
        live_year_one_forecasts=league_year_one,
        mapping=mapping,
        h1_h2_predictor=near,
        h3_predictor=far,
    )
    result = build_live_calendar_shapley_estimates(
        calendar,
        rules=rules,
        permutations=FROZEN_SHAPLEY_PERMUTATIONS,
    )
    estimates = {item.player_id: item for item in result.estimates}
    by_name = {str(row["full_name"]): row for row in league_rows}
    by_id = {str(row["player_id"]): row for row in league_rows}
    fact_by_id = {row.source_player_id: row for row in facts.rows}

    full_rows: list[dict] = []
    bridge_once = True
    all_nonnegative = True
    target_calendar_ok = True
    year1_authority_ok = True
    for coordinate in calendar.forecasts:
        league_row = by_id[coordinate.player_id]
        source_id = mapping.mapped_source_ids[coordinate.player_id]
        source_fact = fact_by_id[source_id]
        estimate = estimates[coordinate.player_id]
        h2 = coordinate.year_2.result
        h3r = coordinate.year_3.result
        bridge_once = bridge_once and (
            h2.model_version.count(FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION) == 1
            and h3r.model_version.count(FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION) == 1
        )
        target_calendar_ok = target_calendar_ok and (
            coordinate.year_1.target_season == 2026
            and coordinate.year_2.target_season == 2027
            and coordinate.year_3.target_season == 2028
        )
        year1_authority_ok = year1_authority_ok and (
            coordinate.year_1.authority == "preserved_preseason_year1_forecast"
            and coordinate.year_1.source == "fsffl:preseason_baseline_league_scored"
        )
        all_nonnegative = all_nonnegative and _finite_nonnegative(
            coordinate.year_1.anticipated_points,
            h2.anticipated_points,
            h3r.anticipated_points,
            estimate.value,
        )
        full_rows.append(
            {
                "player_id": coordinate.player_id,
                "full_name": league_row["full_name"],
                "position": coordinate.position.value,
                "source_age": source_fact.age_years,
                "source_state": source_fact.current_state,
                "source_current_standard_points": source_fact.current_fantasy_points,
                "source_prior_standard_points": source_fact.prior_fantasy_points,
                "year_1_half_ppr": coordinate.year_1.anticipated_points,
                "year_2_half_ppr": h2.anticipated_points,
                "year_3_half_ppr": h3r.anticipated_points,
                "intrinsic_raw": estimate.value,
                "year_1_authority": coordinate.year_1.authority,
                "year_2_model_version": h2.model_version,
                "year_3_model_version": h3r.model_version,
                "year_2_probabilities": dict(h2.probabilities),
                "year_3_probabilities": dict(h3r.probabilities),
                "scoring_multiplier": multipliers[coordinate.position],
            }
        )

    if not (bridge_once and all_nonnegative and target_calendar_ok and year1_authority_ok):
        raise RuntimeError(
            "credibility gate structural invariant failed: "
            f"bridge_once={bridge_once} nonnegative={all_nonnegative} "
            f"calendar={target_calendar_ok} year1_authority={year1_authority_ok}"
        )

    top_te = max(
        (row for row in full_rows if row["position"] == "TE"),
        key=lambda row: (row["year_1_half_ppr"], row["player_id"]),
    )["full_name"]
    sentinel_names = tuple(dict.fromkeys((*BASE_SENTINELS, top_te)))
    sentinels = [
        row for name in sentinel_names for row in full_rows if row["full_name"] == name
    ]

    position_summary = {}
    for position in ("QB", "RB", "WR", "TE"):
        rows = [row for row in full_rows if row["position"] == position]
        position_summary[position] = {
            "count": len(rows),
            "year_1_median": statistics.median(row["year_1_half_ppr"] for row in rows),
            "year_2_median": statistics.median(row["year_2_half_ppr"] for row in rows),
            "year_3_median": statistics.median(row["year_3_half_ppr"] for row in rows),
            "intrinsic_median": statistics.median(row["intrinsic_raw"] for row in rows),
            "top_intrinsic": [
                {
                    "full_name": row["full_name"],
                    "intrinsic_raw": row["intrinsic_raw"],
                    "year_1_half_ppr": row["year_1_half_ppr"],
                    "year_2_half_ppr": row["year_2_half_ppr"],
                    "year_3_half_ppr": row["year_3_half_ppr"],
                }
                for row in sorted(
                    rows,
                    key=lambda item: (-item["intrinsic_raw"], item["player_id"]),
                )[:5]
            ],
        }

    payload = {
        "schema_version": "fsffl-current-player-credibility-board-v1",
        "status": "PASS",
        "purpose": "diagnostic sentinels only; no named-player tuning or promotion authority",
        "evaluation_as_of": as_of.isoformat(),
        "population": len(full_rows),
        "mapped_current_facts": mapping.mapped_count,
        "permutations": result.permutations,
        "seed": result.seed,
        "multipliers": {position.value: value for position, value in multipliers.items()},
        "structural_checks": {
            "identity_population_parity": True,
            "complete_current_fact_mapping": True,
            "year1_preserved_preseason_authority": year1_authority_ok,
            "target_calendar_2026_2027_2028": target_calendar_ok,
            "future_i1_bridge_exactly_once": bridge_once,
            "nonnegative_finite_outputs": all_nonnegative,
            "live_provider_data_used": False,
        },
        "sentinels": sentinels,
        "position_summary": position_summary,
        "full_board": full_rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# FSFFL NEXT - Controlled current-player credibility board",
        "",
        "**Status: PASS**",
        "",
        "Diagnostic only. No current-player result was used to fit, tune, reweight, or alter Forecast/Intrinsic.",
        "",
        "## Structural checks",
        "",
        f"- Population / mapped current facts: {len(full_rows)} / {mapping.mapped_count}",
        f"- Shapley permutations: {result.permutations}",
        "- Frozen Year 1: preserved preseason 0.5-PPR coordinate",
        "- Completed-source I1 inputs: frozen standard/non-PPR coordinate",
        "- Future I1 league-scoring bridge: exactly once",
        "- Live provider data used: no",
        "",
        "## Sentinels",
        "",
        "| Player | Pos | Age | State | Y1 | Y2 | Y3 | Intrinsic | H2 out | H2 starter+ | H2 premium+ |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sentinels:
        p = row["year_2_probabilities"]
        starter_plus = p["starter"] + p["premium"] + p["elite"]
        premium_plus = p["premium"] + p["elite"]
        age = "n/a" if row["source_age"] is None else f"{row['source_age']:.1f}"
        lines.append(
            f"| {row['full_name']} | {row['position']} | {age} | {row['source_state']} | "
            f"{row['year_1_half_ppr']:.1f} | {row['year_2_half_ppr']:.1f} | "
            f"{row['year_3_half_ppr']:.1f} | {row['intrinsic_raw']:.1f} | "
            f"{p['out']:.3f} | {starter_plus:.3f} | {premium_plus:.3f} |"
        )

    lines += ["", "## Cross-position summary", ""]
    for position in ("QB", "RB", "WR", "TE"):
        summary = position_summary[position]
        top = ", ".join(item["full_name"] for item in summary["top_intrinsic"])
        lines.append(
            f"- **{position}** n={summary['count']}: median Y1/Y2/Y3 "
            f"{summary['year_1_median']:.1f}/{summary['year_2_median']:.1f}/{summary['year_3_median']:.1f}; "
            f"median Intrinsic {summary['intrinsic_median']:.1f}; top Intrinsic names: {top}."
        )
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "population": payload["population"],
        "mapped_current_facts": payload["mapped_current_facts"],
        "sentinels": [
            {
                "name": row["full_name"],
                "position": row["position"],
                "year_1": row["year_1_half_ppr"],
                "year_2": row["year_2_half_ppr"],
                "year_3": row["year_3_half_ppr"],
                "intrinsic": row["intrinsic_raw"],
            }
            for row in sentinels
        ],
        "structural_checks": payload["structural_checks"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
