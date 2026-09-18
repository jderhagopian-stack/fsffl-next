from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fsffl.forecast.i1_current_facts import CurrentI1FactsArtifact, map_current_i1_facts
from fsffl.forecast.models import ForecastHorizon, ForecastMetric
from fsffl.product.i1_scoring_bridge import (
    FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION,
    build_future_i1_position_scoring_multipliers,
)
from fsffl.product.runtime import default_live_forecast_loader
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    Position,
    ProviderRef,
    Provenance,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)
from fsffl.value.private_beta_activation_data import (
    ACTIVATION_ARTIFACT_SHA256,
    ACTIVATION_BUNDLE_SHA256,
    ACTIVATION_WORKFLOW_RUN_ID,
    activation_artifact_text,
)

SCHEMA_VERSION = "fsffl-governed-year1-evaluation-universe-v1"
COORDINATE_PREFIX = "year1-current-governed-2026"
RULES_VERSION = "management-12t-half-ppr-superflex-v2:full-current-universe"
SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
SUPPORTED_POSITIONS = {Position.QB, Position.RB, Position.WR, Position.TE}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def diagnostic_rules() -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(
            ScoringRule(stat="pass_yd", points=0.04),
            ScoringRule(stat="pass_td", points=4.0),
            ScoringRule(stat="pass_int", points=-2.0),
            ScoringRule(stat="rush_yd", points=0.1),
            ScoringRule(stat="rush_td", points=6.0),
            ScoringRule(stat="rec", points=0.5),
            ScoringRule(stat="rec_yd", points=0.1),
            ScoringRule(stat="rec_td", points=6.0),
            ScoringRule(stat="fum_lost", points=-2.0),
        ),
    )


def load_sleeper_players() -> dict[str, dict[str, object]]:
    request = urllib.request.Request(SLEEPER_PLAYERS_URL, headers={"User-Agent": "FSFFL-NEXT/research-year1-freeze"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - governed project source
        raw = json.load(response)
    if not isinstance(raw, dict):
        raise ValueError("Sleeper global player response must be a mapping")
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def float_or_none(value: object) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_state(facts: CurrentI1FactsArtifact, sleeper_players: dict[str, dict[str, object]]) -> tuple[LeagueState, dict[str, dict[str, object]]]:
    now = datetime.now(UTC)
    provenance = Provenance(
        source="research-governed-year1-universe",
        retrieved_at=now,
        effective_at=now,
        source_version=RULES_VERSION,
    )
    facts_by_sleeper = {
        str(row.identity_external_id): row
        for row in facts.rows
        if row.identity_provider and row.identity_provider.lower() == "sleeper" and row.identity_external_id
    }
    players: list[Player] = []
    states: list[PlayerState] = []
    status_by_player: dict[str, dict[str, object]] = {}
    for sleeper_id, sleeper in sorted(sleeper_players.items()):
        position_raw = str(sleeper.get("position") or "").upper()
        nfl_team = str(sleeper.get("team") or "").strip().upper() or None
        if position_raw not in {"QB", "RB", "WR", "TE"} or nfl_team is None:
            continue
        position = Position(position_raw)
        display_name = str(
            sleeper.get("full_name")
            or " ".join(filter(None, (sleeper.get("first_name"), sleeper.get("last_name"))))
            or sleeper_id
        ).strip()
        player_id = f"diag:sleeper:{sleeper_id}"
        refs = [ProviderRef(provider="sleeper", external_id=sleeper_id)]
        gsis_id = str(sleeper.get("gsis_id") or "").strip()
        if gsis_id:
            refs.append(ProviderRef(provider="gsis", external_id=gsis_id))
        players.append(
            Player(
                player_id=player_id,
                full_name=display_name,
                position=position,
                nfl_team=nfl_team,
                provider_refs=tuple(refs),
            )
        )
        source = facts_by_sleeper.get(sleeper_id)
        age = source.age_years if source is not None else float_or_none(sleeper.get("age"))
        states.append(
            PlayerState(
                player_id=player_id,
                as_of=now,
                age_years=age,
                nfl_team=nfl_team,
                provenance=provenance,
            )
        )
        status_by_player[player_id] = {
            "status": sleeper.get("status"),
            "injury_status": sleeper.get("injury_status"),
            "practice_participation": sleeper.get("practice_participation"),
            "team": sleeper.get("team"),
        }

    teams = tuple(
        Team(team_id=f"t{index}", league_id="management-diagnostic", display_name=f"Team {index}")
        for index in range(1, 13)
    )
    state = LeagueState(
        league=League(
            league_id="management-diagnostic",
            name="FSFFL NEXT governed downstream evaluation fixture",
            season=facts.evaluation_season,
            rules=diagnostic_rules(),
        ),
        as_of=now,
        teams=teams,
        team_states=tuple(TeamState(team_id=team.team_id, roster=()) for team in teams),
        players=tuple(players),
        player_states=tuple(states),
    )
    return state, status_by_player


def obs_payload(obs) -> dict[str, object]:
    return obs.model_dump(mode="json")


def build(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    facts = CurrentI1FactsArtifact.from_dict(json.loads(activation_artifact_text("current_i1_facts_2026.json")))
    sleeper_players = load_sleeper_players()
    state, status_by_player = build_state(facts, sleeper_players)

    base = {
        "schema_version": SCHEMA_VERSION,
        "coordinate_kind": "fresh current-player downstream evaluation universe; not a reconstruction of prior sentinel",
        "rules_version": RULES_VERSION,
        "evaluation_season": facts.evaluation_season,
        "activation_workflow_run_id": ACTIVATION_WORKFLOW_RUN_ID,
        "activation_bundle_sha256": ACTIVATION_BUNDLE_SHA256,
        "current_i1_facts_sha256": ACTIVATION_ARTIFACT_SHA256["current_i1_facts_2026.json"],
        "state_player_count": len(state.players),
    }

    try:
        evidence = default_live_forecast_loader(state)
    except Exception as exc:
        blocker = {
            **base,
            "status": "BLOCKED_SOURCE_GOVERNANCE",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        (output_dir / "blocker.json").write_bytes(canonical_bytes(blocker))
        (output_dir / "report.md").write_text(
            "# Governed Year-1 universe construction\n\n"
            "Status: **BLOCKED_SOURCE_GOVERNANCE**\n\n"
            f"{type(exc).__name__}: {exc}\n",
            encoding="utf-8",
        )
        return 0

    year_one = tuple(
        item for item in evidence.league_scored_forecasts
        if item.metric == ForecastMetric.FANTASY_POINTS
        and item.horizon == ForecastHorizon.SEASON
        and item.position in SUPPORTED_POSITIONS
    )
    if not year_one:
        blocker = {**base, "status": "BLOCKED_EMPTY_YEAR1", "generated_at": datetime.now(UTC).isoformat()}
        (output_dir / "blocker.json").write_bytes(canonical_bytes(blocker))
        return 0

    as_of_values = {item.as_of.isoformat() for item in year_one}
    if len(as_of_values) != 1:
        blocker = {
            **base,
            "status": "BLOCKED_MIXED_AS_OF",
            "as_of_values": sorted(as_of_values),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        (output_dir / "blocker.json").write_bytes(canonical_bytes(blocker))
        return 0
    freeze_as_of = next(iter(as_of_values))

    year_one_ids = {item.player_id for item in year_one}
    by_player = {player.player_id: player for player in state.players}
    by_state = {item.player_id: item for item in state.player_states}
    unknown = sorted(year_one_ids - set(by_player))
    if unknown:
        blocker = {**base, "status": "BLOCKED_UNKNOWN_CANONICAL_PLAYER", "player_ids": unknown}
        (output_dir / "blocker.json").write_bytes(canonical_bytes(blocker))
        return 0

    scoped = state.model_copy(
        update={
            "players": tuple(player for player in state.players if player.player_id in year_one_ids),
            "player_states": tuple(item for item in state.player_states if item.player_id in year_one_ids),
            "team_states": tuple(
                team_state.model_copy(update={"roster": tuple(entry for entry in team_state.roster if entry.player_id in year_one_ids)})
                for team_state in state.team_states
            ),
        }
    )
    mapping = map_current_i1_facts(scoped, facts)
    if mapping.unmapped_player_ids or mapping.ambiguous_player_ids or mapping.mapped_count != len(year_one_ids):
        blocker = {
            **base,
            "status": "BLOCKED_COMPLETED_SOURCE_MAPPING",
            "freeze_as_of": freeze_as_of,
            "year1_player_count": len(year_one),
            "mapped_count": mapping.mapped_count,
            "unmapped_player_ids": list(mapping.unmapped_player_ids),
            "ambiguous_player_ids": list(mapping.ambiguous_player_ids),
        }
        (output_dir / "blocker.json").write_bytes(canonical_bytes(blocker))
        return 0

    scoring_multipliers = build_future_i1_position_scoring_multipliers(
        raw_forecasts=evidence.raw_forecasts,
        league_year_one=year_one,
        rules=state.league.rules,
    )

    raw_by_player: dict[str, list[object]] = defaultdict(list)
    for item in evidence.raw_forecasts:
        if item.player_id in year_one_ids:
            raw_by_player[item.player_id].append(item)

    rows: list[dict[str, object]] = []
    for item in sorted(year_one, key=lambda x: x.player_id):
        player = by_player[item.player_id]
        pstate = by_state[item.player_id]
        raw_metrics = []
        for raw in sorted(raw_by_player[item.player_id], key=lambda x: (x.metric.value, x.source, x.model_version)):
            raw_metrics.append({
                "metric": raw.metric.value,
                "mean": raw.distribution.mean,
                "stddev": raw.distribution.stddev,
                "source": raw.source,
                "model_version": raw.model_version,
                "as_of": raw.as_of.isoformat(),
                "provenance": raw.provenance.model_dump(mode="json"),
            })
        rows.append({
            "player_id": player.player_id,
            "full_name": player.full_name,
            "position": player.position.value,
            "nfl_team": player.nfl_team,
            "provider_refs": [ref.model_dump(mode="json") for ref in player.provider_refs],
            "player_state": {
                "age_years": pstate.age_years,
                "nfl_team": pstate.nfl_team,
                "as_of": freeze_as_of,
            },
            "eligibility": {"primary_position": player.position.value},
            "status": status_by_player.get(player.player_id, {}),
            "completed_source_player_id": mapping.mapped_source_ids[player.player_id],
            "year1": obs_payload(item),
            "raw_ensemble_metrics": raw_metrics,
        })

    included_ids = {row["player_id"] for row in rows}
    excluded_rows = [
        {
            "player_id": player.player_id,
            "full_name": player.full_name,
            "position": player.position.value,
            "nfl_team": player.nfl_team,
            "reason": "not present in governed Year-1 league-scored board after per-player independent-source and scoring-completeness gates",
        }
        for player in sorted(state.players, key=lambda x: x.player_id)
        if player.player_id not in included_ids
    ]

    rules_payload = state.league.rules.model_dump(mode="json")
    rules_sha256 = sha256_bytes(canonical_bytes(rules_payload))
    position_counts = dict(sorted(Counter(row["position"] for row in rows).items()))
    excluded_position_counts = dict(sorted(Counter(row["position"] for row in excluded_rows).items()))

    coordinate_id = f"{COORDINATE_PREFIX}:{freeze_as_of}"
    universe = {
        "schema_version": SCHEMA_VERSION,
        "coordinate_id": coordinate_id,
        "coordinate_kind": "fresh current-player downstream evaluation universe; not prior-335 reconstruction",
        "freeze_as_of": freeze_as_of,
        "evaluation_season": facts.evaluation_season,
        "league": {
            "league_id": state.league.league_id,
            "name": state.league.name,
            "rules_version": RULES_VERSION,
            "rules": rules_payload,
            "rules_sha256": rules_sha256,
        },
        "source_governance": {
            "evidence_basis": evidence.evidence_basis,
            "successful_source_ids": list(evidence.successful_source_ids),
            "failed_sources": list(evidence.failed_sources),
            "minimum_independent_sources": evidence.runtime_result.coverage.minimum_independent_sources,
            "independent_source_ids": list(evidence.runtime_result.coverage.independent_source_ids),
            "active_source_ids": list(evidence.runtime_result.coverage.active_source_ids),
            "excluded_aggregate_source_ids": list(evidence.runtime_result.coverage.excluded_aggregate_source_ids),
            "excluded_undercovered_groups": evidence.runtime_result.coverage.excluded_undercovered_groups,
            "normalized_observation_count": evidence.runtime_result.coverage.observation_count,
            "live_runtime_model_version": evidence.runtime_result.model_version,
            "live_evidence_model_version": evidence.model_version,
        },
        "downstream_coordinate": {
            "completed_source_mapping_required": True,
            "mapped_completed_source_players": mapping.mapped_count,
            "current_i1_facts_sha256": ACTIVATION_ARTIFACT_SHA256["current_i1_facts_2026.json"],
            "activation_bundle_sha256": ACTIVATION_BUNDLE_SHA256,
            "activation_workflow_run_id": ACTIVATION_WORKFLOW_RUN_ID,
            "future_i1_scoring_bridge_version": FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION,
            "future_i1_position_scoring_multipliers": {
                position.value: value
                for position, value in sorted(scoring_multipliers.items(), key=lambda kv: kv[0].value)
            },
        },
        "row_count": len(rows),
        "position_counts": position_counts,
        "excluded_player_count": len(excluded_rows),
        "excluded_position_counts": excluded_position_counts,
        "rows": rows,
        "exclusions": excluded_rows,
    }

    universe_bytes = canonical_bytes(universe)
    universe_path = output_dir / "governed_year1_universe.json"
    universe_path.write_bytes(universe_bytes)
    universe_sha256 = sha256_bytes(universe_bytes)

    row_material = [
        {
            "player_id": row["player_id"],
            "position": row["position"],
            "year1_mean": row["year1"]["distribution"]["mean"],
            "year1_stddev": row["year1"]["distribution"]["stddev"],
            "year1_as_of": row["year1"]["as_of"],
            "completed_source_player_id": row["completed_source_player_id"],
        }
        for row in rows
    ]
    row_material_sha256 = sha256_bytes(canonical_bytes(row_material))

    manifest = {
        "schema_version": "fsffl-governed-year1-evaluation-universe-manifest-v1",
        "coordinate_id": coordinate_id,
        "freeze_as_of": freeze_as_of,
        "status": "PASS",
        "artifact_path": "governed_year1_universe.json",
        "artifact_sha256": universe_sha256,
        "row_material_sha256": row_material_sha256,
        "row_count": len(rows),
        "position_counts": position_counts,
        "excluded_player_count": len(excluded_rows),
        "excluded_position_counts": excluded_position_counts,
        "source_governance": universe["source_governance"],
        "league_rules_sha256": rules_sha256,
        "activation_bundle_sha256": ACTIVATION_BUNDLE_SHA256,
        "current_i1_facts_sha256": ACTIVATION_ARTIFACT_SHA256["current_i1_facts_2026.json"],
        "serialization": {
            "encoding": "UTF-8",
            "json": "sort_keys=True,separators=(',',':'),ensure_ascii=False",
            "terminator": "single LF",
            "row_order": "ascending canonical player_id",
            "hash": "SHA-256 over exact serialized artifact bytes including terminal LF",
        },
    }
    manifest_bytes = canonical_bytes(manifest)
    manifest_path = output_dir / "governed_year1_universe_manifest.json"
    manifest_path.write_bytes(manifest_bytes)

    reloaded = universe_path.read_bytes()
    if sha256_bytes(reloaded) != universe_sha256:
        raise RuntimeError("fresh reload failed exact artifact SHA-256 verification")
    parsed = json.loads(reloaded)
    if len(parsed["rows"]) != len(rows):
        raise RuntimeError("fresh reload row count differs")
    if parsed["position_counts"] != position_counts:
        raise RuntimeError("fresh reload position counts differ")

    verification = {
        "status": "PASS",
        "coordinate_id": coordinate_id,
        "artifact_sha256_first_write": universe_sha256,
        "artifact_sha256_fresh_reload": sha256_bytes(reloaded),
        "row_count_first_write": len(rows),
        "row_count_fresh_reload": len(parsed["rows"]),
        "position_counts_first_write": position_counts,
        "position_counts_fresh_reload": parsed["position_counts"],
        "manifest_sha256": sha256_bytes(manifest_bytes),
    }
    (output_dir / "reload_verification.json").write_bytes(canonical_bytes(verification))

    report = [
        "# FSFFL NEXT governed Year-1 evaluation universe construction",
        "",
        "Status: **PASS**",
        "",
        f"- Coordinate: `{coordinate_id}`",
        f"- Freeze as-of: `{freeze_as_of}`",
        f"- Rows: **{len(rows)}**; positions: `{position_counts}`",
        f"- Excluded from initial team-assigned skill state: **{len(excluded_rows)}**; positions: `{excluded_position_counts}`",
        f"- Successful governed live sources: `{list(evidence.successful_source_ids)}`",
        f"- Failed/ignored source paths: `{list(evidence.failed_sources)}`",
        f"- Universe SHA-256: `{universe_sha256}`",
        f"- Row-material SHA-256: `{row_material_sha256}`",
        f"- League-rules SHA-256: `{rules_sha256}`",
        f"- Fresh reload SHA-256: `{sha256_bytes(reloaded)}`",
        "",
        "No Intrinsic/Shapley calculation was executed.",
    ]
    (output_dir / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(build(args.output_dir))


if __name__ == "__main__":
    main()
