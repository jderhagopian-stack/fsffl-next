from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fsffl.product.origin_aware_pick_value_runtime import (
    build_live_origin_aware_pick_values,
)
from fsffl.product.runtime import default_live_forecast_loader, default_sleeper_state_loader
from fsffl.product.simulation_runtime import build_live_simulation_analytics
from fsffl.team_utility.simulation import NUMPY_PCG64_BATCHED_GAUSS_V1
from fsffl.value.fsffl_foundation3_pick_curve import (
    FSFFL_FOUNDATION3_CURVES,
    FSFFL_FOUNDATION3_CURVE_MODEL_VERSION,
    FSFFL_FOUNDATION3_TARGET_LEAGUE_ID,
    FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON,
)
from fsffl.value.origin_aware_pick import OriginAwarePickValueStatus


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/foundation3/fsffl_2027_origin_aware_sanity.json"
LEAGUE_ID = FSFFL_FOUNDATION3_TARGET_LEAGUE_ID


def main() -> None:
    state = default_sleeper_state_loader(LEAGUE_ID)
    if state.league.season + 1 != FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON:
        raise RuntimeError(
            "Foundation 3 live curve target season no longer matches current FSFFL State"
        )

    forecast = default_live_forecast_loader(state)
    if not forecast.uncertainty_ready:
        raise RuntimeError(
            "governed live Forecast is not Simulation-ready: "
            + str(forecast.runtime_result.simulation_authority_blockers)
        )
    analytics = build_live_simulation_analytics(
        state,
        forecasts=forecast.league_scored_forecasts,
        forecast_model_version=forecast.model_version,
        simulation_count=50_000,
        seed=20260905,
        rng_protocol=NUMPY_PCG64_BATCHED_GAUSS_V1,
        rng_batch_size=500,
        generated_at=max(datetime.now(UTC), state.as_of),
    )
    simulation = analytics.simulation_result
    if simulation.simulation_count != 50_000:
        raise RuntimeError("real FSFFL sanity did not use the authoritative 50,000-run Simulation")
    if len(simulation.future_pick_distributions) != state.league.rules.team_count:
        raise RuntimeError(
            "real FSFFL Simulation did not emit one origin distribution per team"
        )

    values = build_live_origin_aware_pick_values(state, simulation)
    next_picks = tuple(
        pick
        for pick in state.draft_picks
        if pick.season == FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON
    )
    if len(next_picks) != state.league.rules.team_count * state.league.rules.rookie_draft_rounds:
        raise RuntimeError(
            "canonical 2027 pick inventory is not complete for all league teams/rounds"
        )
    by_pick = {row.pick_id: row for row in values}
    if set(by_pick) != {pick.pick_id for pick in state.draft_picks}:
        raise RuntimeError("live origin-aware Value result does not cover canonical pick inventory")

    curve_by_round = {
        curve.round: {row.slot_in_round: row for row in curve.slots}
        for curve in FSFFL_FOUNDATION3_CURVES
    }
    ownership = {row.pick_id: row.owner_team_id for row in state.pick_ownership}
    team_names = {team.team_id: team.display_name for team in state.teams}
    sanity_rows = []
    nonlinear_examples = []
    transferred = 0
    for pick in sorted(next_picks, key=lambda item: (item.round, item.original_team_id)):
        result = by_pick[pick.pick_id]
        if (
            result.status != OriginAwarePickValueStatus.ORIGIN_AWARE_AUTHORITATIVE
            or not result.authoritative
            or result.origin_aware_estimate is None
        ):
            raise RuntimeError(
                f"2027 pick {pick.pick_id} is not authoritative: {result.status}"
            )
        if result.class_strength_status != "not_applied_no_governed_evidence":
            raise RuntimeError("Foundation 3 unexpectedly applied a class-strength assumption")
        if result.horizon_adjustment_status != "not_applied_no_governed_evidence":
            raise RuntimeError("Foundation 3 unexpectedly applied a horizon assumption")
        if result.slot_value_curve_model_version != FSFFL_FOUNDATION3_CURVE_MODEL_VERSION:
            raise RuntimeError("live pick did not use the frozen Foundation 3 exact-slot curve")

        manual_mean = sum(
            probability.probability
            * curve_by_round[pick.round][probability.slot_in_round].value.mean
            for probability in result.slot_probabilities
        )
        if abs(manual_mean - result.origin_aware_estimate.distribution.mean) > 1e-9:
            raise RuntimeError(
                f"pick {pick.pick_id} value diverges from exact probability mixture"
            )

        rounded_slot = min(
            state.league.rules.team_count,
            max(1, int(round(result.expected_slot or 1.0))),
        )
        rounded_lookup = curve_by_round[pick.round][rounded_slot].value.mean
        if (
            len(result.slot_probabilities) > 1
            and abs(manual_mean - rounded_lookup) > 1e-6
        ):
            nonlinear_examples.append(
                {
                    "pick_id": pick.pick_id,
                    "round": pick.round,
                    "original_team_id": pick.original_team_id,
                    "expected_slot": result.expected_slot,
                    "rounded_slot": rounded_slot,
                    "exact_mixture_mean": manual_mean,
                    "rounded_expected_slot_value": rounded_lookup,
                }
            )

        owner = ownership[pick.pick_id]
        if owner != pick.original_team_id:
            transferred += 1
        sanity_rows.append(
            {
                "pick_id": pick.pick_id,
                "round": pick.round,
                "origin_team_id": pick.original_team_id,
                "origin_team_name": team_names.get(pick.original_team_id, pick.original_team_id),
                "owner_team_id": owner,
                "owner_team_name": team_names.get(owner, owner),
                "expected_slot": result.expected_slot,
                "median_slot": result.median_slot,
                "value_mean": result.origin_aware_estimate.distribution.mean,
                "value_stddev": result.origin_aware_estimate.distribution.stddev,
                "dependency_fingerprint": result.dependency_fingerprint,
            }
        )

    if not nonlinear_examples:
        raise RuntimeError(
            "real 2027 distributions did not exercise the nonlinear exact-mixture sanity"
        )
    if transferred == 0:
        raise RuntimeError(
            "real FSFFL 2027 inventory did not exercise origin-vs-owner separation"
        )

    round_one = sorted(
        (row for row in sanity_rows if row["round"] == 1),
        key=lambda row: (row["expected_slot"], row["origin_team_name"]),
    )
    manifest = {
        "schema_version": "foundation3-fsffl-2027-origin-aware-sanity-v1",
        "captured_at": datetime.now(UTC).isoformat(),
        "league_id": state.league.league_id,
        "league_name": state.league.name,
        "league_state_id": state.state_id,
        "draft_season": FSFFL_FOUNDATION3_TARGET_DRAFT_SEASON,
        "simulation_count": simulation.simulation_count,
        "simulation_model_version": simulation.model_version,
        "simulation_input_fingerprint": simulation.simulation_input_fingerprint,
        "rng_protocol": simulation.rng_protocol,
        "rng_batch_size": simulation.rng_batch_size,
        "curve_model_version": FSFFL_FOUNDATION3_CURVE_MODEL_VERSION,
        "curve_scale": FSFFL_FOUNDATION3_CURVES[0].scale.model_dump(mode="json"),
        "origin_distribution_count": len(simulation.future_pick_distributions),
        "authoritative_2027_pick_count": len(sanity_rows),
        "transferred_2027_pick_count": transferred,
        "nonlinear_exact_mixture_example_count": len(nonlinear_examples),
        "nonlinear_exact_mixture_examples": nonlinear_examples[:5],
        "round_one_by_expected_slot": round_one,
        "all_2027_picks": sanity_rows,
        "class_strength_adjustment": "not_applied_no_governed_evidence",
        "horizon_adjustment": "not_applied_no_governed_evidence",
        "broad_market_early_mid_late_used": False,
        "status": "PASS",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "league_state_id": state.state_id,
        "authoritative_2027_pick_count": len(sanity_rows),
        "transferred_2027_pick_count": transferred,
        "nonlinear_exact_mixture_example_count": len(nonlinear_examples),
        "round_one": round_one,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
