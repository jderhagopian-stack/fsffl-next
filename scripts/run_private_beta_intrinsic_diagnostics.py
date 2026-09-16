from __future__ import annotations

import argparse
import json
import time
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.forecast.i1_current_facts import CurrentI1FactsArtifact
from fsffl.forecast.integrated_i1 import age_band
from fsffl.product.private_beta_shapley_runtime import PrivateBetaShapleyContractLoader
from fsffl.product.runtime import (
    PrivateBetaRuntimeStore,
    UserRuntimeContext,
    default_live_forecast_loader,
)
from fsffl.product.shapley_intrinsic_routes import install_shapley_intrinsic_routes
from fsffl.product.webapp import require_beta_user
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
    ACTIVATION_BUNDLE_SHA256,
    ACTIVATION_WORKFLOW_RUN_ID,
    activation_artifact_text,
)
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability

_DIAGNOSTIC_RULES_VERSION = "management-12t-half-ppr-superflex-v1"
_SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"


def _load_sleeper_players() -> dict[str, dict[str, object]]:
    request = urllib.request.Request(_SLEEPER_PLAYERS_URL, headers={"User-Agent": "FSFFL-NEXT/diagnostic"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - governed public beta source
        raw = json.load(response)
    if not isinstance(raw, dict):
        raise ValueError("Sleeper global player response must be a mapping")
    return {str(key): value for key, value in raw.items() if isinstance(value, dict)}


def _diagnostic_rules() -> LeagueRules:
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


def _build_diagnostic_state(
    facts: CurrentI1FactsArtifact,
    sleeper_players: dict[str, dict[str, object]],
) -> tuple[LeagueState, dict[str, dict[str, object]], dict[str, object]]:
    now = datetime.now(UTC)
    provenance = Provenance(
        source="private-beta-management-diagnostic",
        retrieved_at=now,
        effective_at=now,
        source_version=_DIAGNOSTIC_RULES_VERSION,
    )
    players: list[Player] = []
    states: list[PlayerState] = []
    raw_status: dict[str, dict[str, object]] = {}
    source_by_player: dict[str, object] = {}
    for row in facts.rows:
        external_id = row.identity_external_id
        sleeper = sleeper_players.get(str(external_id), {}) if external_id else {}
        player_id = f"diag:{row.source_player_id}"
        nfl_team = str(sleeper.get("team") or "").strip().upper() or None
        players.append(
            Player(
                player_id=player_id,
                full_name=row.display_name,
                position=row.position,
                nfl_team=nfl_team,
                provider_refs=(
                    ProviderRef(
                        provider=str(row.identity_provider or "sleeper"),
                        external_id=str(external_id or row.source_player_id),
                    ),
                ),
            )
        )
        states.append(
            PlayerState(
                player_id=player_id,
                as_of=now,
                age_years=row.age_years,
                nfl_team=nfl_team,
                provenance=provenance,
            )
        )
        raw_status[player_id] = {
            "status": sleeper.get("status"),
            "injury_status": sleeper.get("injury_status"),
            "practice_participation": sleeper.get("practice_participation"),
            "team": sleeper.get("team"),
        }
        source_by_player[player_id] = row

    teams = tuple(
        Team(team_id=f"t{index}", league_id="management-diagnostic", display_name=f"Team {index}")
        for index in range(1, 13)
    )
    league = League(
        league_id="management-diagnostic",
        name="FSFFL NEXT management validation fixture",
        season=facts.evaluation_season,
        rules=_diagnostic_rules(),
    )
    state = LeagueState(
        league=league,
        as_of=now,
        teams=teams,
        team_states=tuple(TeamState(team_id=team.team_id, roster=()) for team in teams),
        players=tuple(players),
        player_states=tuple(states),
    )
    return state, raw_status, source_by_player


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * p
    lo = int(index)
    hi = min(len(ordered) - 1, lo + 1)
    fraction = index - lo
    return ordered[lo] * (1.0 - fraction) + ordered[hi] * fraction


def _distribution(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "p10": _percentile(values, 0.10),
        "p25": _percentile(values, 0.25),
        "median": _percentile(values, 0.50),
        "p75": _percentile(values, 0.75),
        "p90": _percentile(values, 0.90),
        "max": max(values) if values else None,
    }


def _explicit_absence(status: dict[str, object]) -> bool:
    injury = str(status.get("injury_status") or "").strip().lower()
    base = str(status.get("status") or "").strip().lower()
    practice = str(status.get("practice_participation") or "").strip().lower()
    return bool(
        injury in {"ir", "out", "pup", "nfi", "suspended", "doubtful", "questionable"}
        or any(token in base for token in ("injured", "reserve", "pup", "suspend", "inactive"))
        or practice in {"did not participate", "limited participation"}
    )


def _archetypes(row, status: dict[str, object]) -> set[str]:
    output: set[str] = set()
    if row.current_state == "elite":
        output.add("elite")
    if row.role_band == "established" and row.current_state in {"starter", "premium", "elite"}:
        output.add("established")
    if row.experience_years is not None and 1 <= row.experience_years <= 3 and row.current_state in {"depth", "usable", "starter"}:
        output.add("developmental")
    if row.experience_years == 0:
        output.add("rookie")
    if age_band(row.position, row.age_years) == "aging":
        output.add("aging")
    if _explicit_absence(status):
        output.add("injured_or_temporarily_absent")
    if row.current_state == "depth":
        output.add("backup")
    if row.current_state == "out" or row.role_band == "weak":
        output.add("fringe")
    return output


def _rank_rows(contract, state: LeagueState, source_by_player: dict[str, object], raw_status: dict[str, dict[str, object]]):
    by_player = {player.player_id: player for player in state.players}
    ordered = sorted(contract.estimates, key=lambda item: (-item.raw_intrinsic_value, item.player_id))
    positional_counter: dict[str, int] = defaultdict(int)
    rows: list[dict[str, object]] = []
    for overall_rank, estimate in enumerate(ordered, start=1):
        player = by_player[estimate.player_id]
        positional_counter[player.position.value] += 1
        evidence_paths = [item.uncertainty.evidence_path for item in estimate.contributions[1:]]
        evidence_path = "rich" if evidence_paths and all(path == "rich" for path in evidence_paths) else "reduced"
        source = source_by_player[estimate.player_id]
        raw = estimate.raw_intrinsic_value
        rows.append(
            {
                "player_id": estimate.player_id,
                "player": player.full_name,
                "position": player.position.value,
                "raw_intrinsic": raw,
                "year_1_raw": estimate.contributions[0].raw_shapley_contribution,
                "year_2_raw": estimate.contributions[1].raw_shapley_contribution,
                "year_3_raw": estimate.contributions[2].raw_shapley_contribution,
                "year_1_discounted": estimate.contributions[0].discounted_contribution,
                "year_2_discounted": estimate.contributions[1].discounted_contribution,
                "year_3_discounted": estimate.contributions[2].discounted_contribution,
                "evidence_path": evidence_path,
                "overall_rank": overall_rank,
                "positional_rank": positional_counter[player.position.value],
                "current_state": source.current_state,
                "role_band": source.role_band,
                "age_years": source.age_years,
                "experience_years": source.experience_years,
                "archetypes": sorted(_archetypes(source, raw_status.get(estimate.player_id, {}))),
                "explicit_status_evidence": raw_status.get(estimate.player_id, {}),
            }
        )
    return rows


def _pick_archetype_examples(rows: list[dict[str, object]], count: int = 3) -> dict[str, list[dict[str, object]]]:
    names = (
        "elite",
        "established",
        "developmental",
        "rookie",
        "aging",
        "injured_or_temporarily_absent",
        "backup",
        "fringe",
    )
    return {
        name: [row for row in rows if name in row["archetypes"]][:count]
        for name in names
    }


def _markdown_table(rows: list[dict[str, object]], include_scale: bool = False) -> list[str]:
    header = "| # | Player | Pos | Raw Intrinsic | Y1 | Y2 | Y3 | Evidence | Pos rank"
    if include_scale:
        header += " | Display"
    header += " |"
    divider = "|---:|---|:---:|---:|---:|---:|---:|:---:|---:|"
    if include_scale:
        divider += "---:|"
    lines = [header, divider]
    for row in rows:
        line = (
            f"| {row['overall_rank']} | {row['player']} | {row['position']} | {row['raw_intrinsic']:.2f} | "
            f"{row['year_1_raw']:.2f} | {row['year_2_raw']:.2f} | {row['year_3_raw']:.2f} | "
            f"{row['evidence_path']} | {row['positional_rank']}"
        )
        if include_scale:
            line += f" | {row['display_0_10000']:.0f}"
        lines.append(line + " |")
    return lines


def run(output_json: Path, output_md: Path) -> None:
    facts_raw = json.loads(activation_artifact_text("current_i1_facts_2026.json"))
    facts = CurrentI1FactsArtifact.from_dict(facts_raw)
    sleeper_players = _load_sleeper_players()
    state, raw_status, source_by_player = _build_diagnostic_state(facts, sleeper_players)

    forecast_started = time.perf_counter()
    forecast_evidence = default_live_forecast_loader(state)
    forecast_seconds = time.perf_counter() - forecast_started
    if len(forecast_evidence.successful_source_ids) < 2:
        raise RuntimeError("governed live Forecast requires at least two successful projection sources")

    # Advance only the diagnostic snapshot timestamp past the freshly acquired
    # forecasts so the normal runtime store can enforce evidence-cutoff ordering.
    max_as_of = max(
        (item.as_of for item in forecast_evidence.raw_forecasts + forecast_evidence.league_scored_forecasts),
        default=state.as_of,
    )
    state = state.model_copy(update={"as_of": max(state.as_of, max_as_of + timedelta(microseconds=1))})
    context = UserRuntimeContext(
        user_id="management-diagnostic",
        league_state=state,
        forecast_evidence=forecast_evidence,
    )

    loader = PrivateBetaShapleyContractLoader()
    cold_started = time.perf_counter()
    contract = loader(context)
    cold_seconds = time.perf_counter() - cold_started
    warm_started = time.perf_counter()
    warm_contract = loader(context)
    warm_seconds = time.perf_counter() - warm_started
    if contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE:
        raise RuntimeError(f"Shapley Intrinsic diagnostic is unavailable: {contract.status_reason}")
    if warm_contract is not contract:
        raise RuntimeError("identical runtime evidence did not reuse the immutable Shapley contract")
    if contract.display_scaling_applied:
        raise RuntimeError("raw Shapley contract must not apply display scaling")

    # Exercise the actual FastAPI route with the same normal runtime-store contract.
    store = PrivateBetaRuntimeStore()
    store.set_league_state("management-diagnostic", state)
    store.set_forecast_evidence("management-diagnostic", forecast_evidence)
    endpoint_loader = PrivateBetaShapleyContractLoader()
    app = FastAPI()
    app.dependency_overrides[require_beta_user] = lambda: "management-diagnostic"
    install_shapley_intrinsic_routes(app, runtime_store=store, contract_loader=endpoint_loader)
    client = TestClient(app)
    endpoint_cold_started = time.perf_counter()
    response = client.get("/api/value/intrinsic-shapley-v1")
    endpoint_cold_seconds = time.perf_counter() - endpoint_cold_started
    if response.status_code != 200:
        raise RuntimeError(f"Shapley endpoint smoke failed: HTTP {response.status_code}: {response.text}")
    endpoint_payload = response.json()
    endpoint_warm_started = time.perf_counter()
    warm_response = client.get("/api/value/intrinsic-shapley-v1")
    endpoint_warm_seconds = time.perf_counter() - endpoint_warm_started
    if warm_response.status_code != 200:
        raise RuntimeError(f"warm Shapley endpoint smoke failed: HTTP {warm_response.status_code}")
    if endpoint_payload.get("display_scaling_applied") is not False:
        raise RuntimeError("endpoint raw contract unexpectedly applies display scaling")

    rows = _rank_rows(contract, state, source_by_player, raw_status)
    if not rows:
        raise RuntimeError("live Shapley sanity board is empty")
    top_reference = max(float(row["raw_intrinsic"]) for row in rows)
    if top_reference <= 0:
        raise RuntimeError("linear display diagnostic requires a positive governed top-current-player reference")
    for row in rows:
        row["display_0_10000"] = 10000.0 * max(0.0, float(row["raw_intrinsic"])) / top_reference

    by_position: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_position[str(row["position"])].append(row)

    positional_distribution = {
        position: {
            "raw": _distribution([float(row["raw_intrinsic"]) for row in position_rows]),
            "display_0_10000": _distribution([float(row["display_0_10000"]) for row in position_rows]),
        }
        for position, position_rows in sorted(by_position.items())
    }
    starter_rows = [row for row in rows if row["current_state"] in {"starter", "premium", "elite"}]
    bench_rows = [row for row in rows if row["current_state"] in {"usable", "depth"}]
    fringe_rows = [row for row in rows if row["current_state"] == "out" or row["role_band"] == "weak"]
    group_distributions = {
        "starter": _distribution([float(row["display_0_10000"]) for row in starter_rows]),
        "bench": _distribution([float(row["display_0_10000"]) for row in bench_rows]),
        "fringe": _distribution([float(row["display_0_10000"]) for row in fringe_rows]),
    }

    report = {
        "status": "PASS",
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "management diagnostic only; no model or market calibration",
        "diagnostic_rules_version": _DIAGNOSTIC_RULES_VERSION,
        "activation_bundle_sha256": ACTIVATION_BUNDLE_SHA256,
        "activation_workflow_run_id": ACTIVATION_WORKFLOW_RUN_ID,
        "contract": {
            "status": contract.status.value,
            "player_count": contract.coverage.player_count,
            "target_years": list(contract.target_years),
            "display_scaling_applied": contract.display_scaling_applied,
            "diagnostic_h1_included": contract.diagnostic_h1_included,
            "missing_required_fact_families": list(contract.coverage.missing_required_fact_families),
        },
        "live_forecast": {
            "successful_sources": list(forecast_evidence.successful_source_ids),
            "failed_sources": list(forecast_evidence.failed_sources),
            "forecast_acquisition_seconds": forecast_seconds,
            "year_1_player_count": contract.coverage.year_1_forecast_players,
        },
        "latency_seconds": {
            "contract_cold": cold_seconds,
            "contract_warm_cached": warm_seconds,
            "endpoint_cold": endpoint_cold_seconds,
            "endpoint_warm_cached": endpoint_warm_seconds,
        },
        "sanity_board": {
            "top_30_overall": rows[:30],
            "top_by_position": {position: position_rows[:10] for position, position_rows in sorted(by_position.items())},
            "archetype_examples": _pick_archetype_examples(rows),
            "archetype_policy": {
                "elite": "canonical completed-source current_state=elite",
                "established": "canonical role_band=established and state starter/premium/elite",
                "developmental": "1-3 years experience and state depth/usable/starter",
                "rookie": "experience_years=0",
                "aging": "governed I1 age_band=aging",
                "injured_or_temporarily_absent": "explicit current Sleeper injury/status/practice metadata only; never inferred from missing data",
                "backup": "canonical current_state=depth",
                "fringe": "canonical current_state=out or role_band=weak",
            },
        },
        "display_scale_diagnostic": {
            "formula": "display = 10000 * raw_intrinsic / governed_top_current_player_raw_intrinsic",
            "top_reference_player": rows[0]["player"],
            "top_reference_raw_intrinsic": top_reference,
            "raw_contract_unchanged": True,
            "market_inputs_used": False,
            "overall_raw_distribution": _distribution([float(row["raw_intrinsic"]) for row in rows]),
            "overall_display_distribution": _distribution([float(row["display_0_10000"]) for row in rows]),
            "positional_distributions": positional_distribution,
            "starter_bench_fringe_display_distributions": group_distributions,
            "representative_examples": {
                "starter": starter_rows[:5],
                "bench": bench_rows[:5],
                "fringe": fringe_rows[:5],
            },
            "management_note": "Linear mapping only. No nonlinear transformation is fit or proposed by this diagnostic.",
        },
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md: list[str] = [
        "# FSFFL NEXT private-beta Intrinsic live diagnostics",
        "",
        f"Status: **{report['status']}**",
        "",
        "This is management diagnostics only. It does not tune Forecast, I1, Shapley, Team Utility, Decision, or market alignment.",
        "",
        "## Coverage and latency",
        "",
        f"- Contract status: `{contract.status.value}`; players: {contract.coverage.player_count}; target years: {contract.target_years}.",
        f"- Live Forecast sources: {', '.join(forecast_evidence.successful_source_ids)}; failures: {', '.join(forecast_evidence.failed_sources) or 'none'}.",
        f"- Forecast acquisition: {forecast_seconds:.3f}s; contract cold: {cold_seconds:.3f}s; warm cache: {warm_seconds:.6f}s.",
        f"- HTTP endpoint cold: {endpoint_cold_seconds:.3f}s; warm cache: {endpoint_warm_seconds:.6f}s.",
        f"- Missing rich fact families: {', '.join(contract.coverage.missing_required_fact_families) or 'none'}.",
        "",
        "## Top 30 live player sanity board",
        "",
        *_markdown_table(rows[:30], include_scale=True),
        "",
        "## Top players by position",
        "",
    ]
    for position, position_rows in sorted(by_position.items()):
        md.extend([f"### {position}", "", *_markdown_table(position_rows[:10], include_scale=True), ""])
    md.extend([
        "## Archetype examples",
        "",
    ])
    archetypes = _pick_archetype_examples(rows)
    for archetype, examples in archetypes.items():
        md.append(f"### {archetype}")
        md.append("")
        if examples:
            md.extend(_markdown_table(examples, include_scale=True))
        else:
            md.append("No player in the live governed universe met this evidence-backed diagnostic classification.")
        md.append("")
    md.extend([
        "## 0-10,000 linear display diagnostic",
        "",
        "Raw Shapley remains authoritative and `display_scaling_applied=false`. This display candidate is management-only.",
        "",
        f"Formula: `display = 10000 * raw / {top_reference:.6f}` (the governed current leader, {rows[0]['player']}, maps to 10,000).",
        "",
        f"Overall display distribution: `{json.dumps(report['display_scale_diagnostic']['overall_display_distribution'], sort_keys=True)}`",
        "",
        f"Starter/bench/fringe display distributions: `{json.dumps(group_distributions, sort_keys=True)}`",
        "",
        "No market/KTC/ADP inputs were used and no nonlinear display transformation was fit.",
        "",
    ])
    output_md.write_text("\n".join(md), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    run(args.output_json, args.output_md)


if __name__ == "__main__":
    main()
