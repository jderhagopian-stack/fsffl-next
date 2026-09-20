from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product.i1_player_scoring import translate_future_i1_result
from fsffl.product.league_value_lens_routes import install_league_value_lens_routes
from fsffl.product.league_value_lenses import build_league_value_lenses
from fsffl.product.p0_forecast_runtime import frozen_p0_standard_materialization
from fsffl.product.runtime import PrivateBetaRuntimeStore, UserRuntimeContext, default_sleeper_state_loader
from fsffl.state.models import LeagueRules, Position
from fsffl.value.current_runtime import build_current_market_values
from fsffl.value.shapley_intrinsic import FutureStateForecast, PlayerIntrinsicForecast, build_intrinsic_shapley_estimates
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability


ROOT = Path(__file__).resolve().parents[1]
LEAGUE_ID = "1312071960615731200"
SOURCE = ROOT / "artifacts/implementation/corrected_p0_preseason_credibility_gate_20260919/RECONCILED_PRESEASON_SOURCE_335.csv"
OUT = ROOT / "artifacts/diagnostics/forecast_value_reconciliation_20260920"


def _future(result) -> FutureStateForecast:
    return FutureStateForecast(
        probabilities=result.probabilities,
        state_means=result.state_means,
        anticipated_points=result.anticipated_points,
    )


def _load_rows() -> list[dict[str, str]]:
    with SOURCE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _intrinsic_contract(rows: list[dict[str, str]], rules: LeagueRules):
    p0 = frozen_p0_standard_materialization()
    forecasts: list[PlayerIntrinsicForecast] = []
    for row in rows:
        canonical_id = row["player_id"]
        p0_id = row["current_player_id"]
        standard_y1 = float(row["y1_points"])
        league_y1 = float(row["league_y1_points"])
        multiplier = league_y1 / standard_y1
        player = p0.players[p0_id]
        forecasts.append(
            PlayerIntrinsicForecast(
                player_id=canonical_id,
                position=Position(row["position"]),
                current_points=league_y1,
                year_2=_future(translate_future_i1_result(player.result_for(2), multiplier=multiplier)),
                year_3=_future(translate_future_i1_result(player.result_for(3), multiplier=multiplier)),
            )
        )
    estimates = build_intrinsic_shapley_estimates(tuple(forecasts), rules=rules)
    return SimpleNamespace(
        status=ShapleyIntrinsicAvailability.READY,
        status_reason=None,
        contract_version="intrinsic-shapley-contract-v2:effective-horizon-seeds",
        quantity_semantics="raw_governed_shapley_marginal_fantasy_points",
        intrinsic_model_version=estimates[0].model_version if estimates else None,
        forecast_model_version="p0-final-route-authority-v1:cf5e3c0d375c",
        estimates=tuple(
            SimpleNamespace(player_id=item.player_id, raw_intrinsic_value=float(item.value))
            for item in estimates
        ),
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    state = default_sleeper_state_loader(LEAGUE_ID)
    rows = _load_rows()
    market = build_current_market_values(state)
    intrinsic = _intrinsic_contract(rows, state.league.rules)

    runtime = UserRuntimeContext(
        user_id="audit-user",
        league_state=state,
        value_evidence=market,
    )
    payload = build_league_value_lenses(runtime, intrinsic)

    assert payload["authority"]["broad_market_and_intrinsic_are_distinct_lenses"] is True
    assert payload["authority"]["raw_value_subtraction_used"] is False
    assert payload["authority"]["team_value_total_created"] is False
    assert payload["authority"]["league_market_value_available"] is False
    assert payload["authority"]["team_utility_included"] is False
    assert payload["authority"]["fsffl_cardinal_value_included"] is False

    comparable = [row for row in payload["players"] if row["comparison_available"]]
    if not comparable:
        raise RuntimeError("real-roster audit produced no comparable Market/Intrinsic players")
    for row in comparable:
        expected = row["intrinsic_percentile"] - row["broad_market_percentile"]
        if abs(row["percentile_gap"] - expected) > 1e-12:
            raise RuntimeError(f"percentile gap mismatch for {row['player_id']}")

    intrinsic_only = build_league_value_lenses(
        UserRuntimeContext(user_id="audit-user", league_state=state),
        intrinsic,
    )
    if intrinsic_only["broad_market"]["status"] != "unavailable":
        raise RuntimeError("Broad Market did not fail independently")
    if intrinsic_only["fsffl_intrinsic"]["status"] != "ready":
        raise RuntimeError("Intrinsic should remain independently ready")

    unavailable_intrinsic = SimpleNamespace(
        status=ShapleyIntrinsicAvailability.UNAVAILABLE,
        status_reason="audit forced unavailable",
        contract_version=intrinsic.contract_version,
        quantity_semantics=intrinsic.quantity_semantics,
        intrinsic_model_version=intrinsic.intrinsic_model_version,
        forecast_model_version=intrinsic.forecast_model_version,
        estimates=(),
    )
    market_only = build_league_value_lenses(runtime, unavailable_intrinsic)
    if market_only["broad_market"]["status"] != "ready":
        raise RuntimeError("Broad Market should remain independently ready")
    if market_only["fsffl_intrinsic"]["status"] != "unavailable":
        raise RuntimeError("Intrinsic did not fail independently")

    store = PrivateBetaRuntimeStore()
    store.set_league_state("audit-user", state)
    store.set_value_evidence("audit-user", market)
    app = FastAPI()
    install_league_value_lens_routes(
        app,
        runtime_store=store,
        contract_loader=lambda _context: intrinsic,
        require_user=lambda: "audit-user",
    )
    response = TestClient(app).get("/api/league/value-lenses")
    if response.status_code != 200:
        raise RuntimeError(f"route audit failed: {response.status_code} {response.text}")
    route_payload = response.json()
    if route_payload["contract_version"] != payload["contract_version"]:
        raise RuntimeError("HTTP route contract version differs from direct builder")

    player_by_id = {p.player_id: p for p in state.players}
    sample = sorted(
        comparable,
        key=lambda row: (-abs(float(row["percentile_gap"])), str(row["full_name"])),
    )[:24]
    sample_rows = [
        {
            "team": row["owner_team_name"],
            "player": row["full_name"],
            "position": row["position"],
            "broad_market_percentile": row["broad_market_percentile"],
            "intrinsic_percentile": row["intrinsic_percentile"],
            "intrinsic_minus_market_pct_points": row["percentile_gap"] * 100.0,
        }
        for row in sample
    ]
    with (OUT / "LEAGUE_VALUE_LENS_REAL_ROSTER_SAMPLE.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(sample_rows[0]))
        writer.writeheader()
        writer.writerows(sample_rows)

    manifest = {
        "schema_version": "fsffl-league-value-lens-real-roster-audit-v1",
        "run_at": datetime.now(UTC).isoformat(),
        "sleeper_league_id": LEAGUE_ID,
        "league_name": state.league.name,
        "team_count": len(state.teams),
        "rostered_player_rows": len(payload["players"]),
        "comparable_player_rows": len(comparable),
        "broad_market_status": payload["broad_market"]["status"],
        "intrinsic_status": payload["fsffl_intrinsic"]["status"],
        "broad_market_player_count": payload["broad_market"]["player_count"],
        "intrinsic_player_count": payload["fsffl_intrinsic"]["player_count"],
        "market_sources": list(market.successful_source_ids),
        "market_failures": list(market.failed_sources),
        "direct_builder_status": payload["status"],
        "http_route_status_code": response.status_code,
        "http_route_contract_version": route_payload["contract_version"],
        "independent_unavailability": {
            "market_missing_intrinsic_status": intrinsic_only["fsffl_intrinsic"]["status"],
            "market_missing_market_status": intrinsic_only["broad_market"]["status"],
            "intrinsic_missing_market_status": market_only["broad_market"]["status"],
            "intrinsic_missing_intrinsic_status": market_only["fsffl_intrinsic"]["status"],
        },
        "forbidden_authorities": {
            "team_value_total_created": payload["authority"]["team_value_total_created"],
            "team_value_rank_created": payload["authority"]["team_value_rank_created"],
            "league_market_value_available": payload["authority"]["league_market_value_available"],
            "team_utility_included": payload["authority"]["team_utility_included"],
            "fsffl_cardinal_value_included": payload["authority"]["fsffl_cardinal_value_included"],
            "recommendation_authority": payload["authority"]["recommendation_authority"],
            "acceptance_probability": payload["authority"]["acceptance_probability"],
        },
        "sample": sample_rows,
    }
    (OUT / "LEAGUE_VALUE_LENS_REAL_ROSTER_AUDIT.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
