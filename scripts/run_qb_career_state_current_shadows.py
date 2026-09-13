from __future__ import annotations

"""Run current-player QB career-state shadows through live FSFFL Forecast providers.

This is a production-shape safety check only. Named players are preselected to span
roles; no model coefficient, threshold, feature, or policy is tuned from the result.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from fsffl.forecast.current_runtime import build_current_live_forecasts
from fsffl.forecast.intrinsic_v1 import materialize_intrinsic_v1_forecast_path
from fsffl.forecast.qb_career_state import _evidence_payload, rank_percentiles
from fsffl.forecast.qb_career_state_runtime import forecast_qb_career_state_runtime
from fsffl.state.models import (
    League, LeagueRules, LeagueState, LineupRequirement, Player, PlayerState,
    Position, Provenance, RosterSlot, ScoringRule,
)
from fsffl.value.intrinsic_v1 import estimate_intrinsic_value_v1

# Frozen before shadow inspection. Ages are 2026 age-year floors, matching the
# historical research feature rather than introducing a continuous-age change.
SHADOWS = {
    "elite_established": ("Josh Allen", 30.0),
    "young_highly_drafted": ("Drake Maye", 24.0),
    "veteran_established": ("Dak Prescott", 33.0),
    "fringe_competition": ("Daniel Jones", 29.0),
    "backup_uncertain": ("Malik Willis", 27.0),
    "rushing_heavy": ("Lamar Jackson", 29.0),
}


def _rules() -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=10,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=1),
            LineupRequirement(slot=RosterSlot.WR, count=1),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(
            ScoringRule(stat="pass_yd", points=0.04),
            ScoringRule(stat="pass_td", points=4.0),
            ScoringRule(stat="pass_int", points=-2.0),
            ScoringRule(stat="rush_yd", points=0.1),
            ScoringRule(stat="rush_td", points=6.0),
            ScoringRule(stat="fum_lost", points=-2.0),
        ),
    )


def _state(now: datetime) -> LeagueState:
    payload = _evidence_payload()
    players = []
    states = []
    age_by_name = {name: age for name, age in SHADOWS.values()}
    for gsis_id, row in payload["players"].items():
        name = str(row.get("display_name") or gsis_id)
        pid = f"shadow:{gsis_id}"
        players.append(Player(player_id=pid, full_name=name, position=Position.QB))
        states.append(PlayerState(
            player_id=pid,
            as_of=now,
            age_years=age_by_name.get(name, 28.0),
            provenance=Provenance(source="qb-shadow", retrieved_at=now, effective_at=now),
        ))
    return LeagueState(
        league=League(league_id="qb-shadow", name="QB Shadow", season=2026, rules=_rules()),
        as_of=now,
        teams=(),
        team_states=(),
        players=tuple(players),
        player_states=tuple(states),
        provenance=(Provenance(source="qb-shadow", retrieved_at=now, effective_at=now),),
    )


def _dummy_paths(now: datetime, after: bool):
    paths = {}
    for pos in (Position.RB, Position.WR, Position.TE):
        for idx in range(12):
            pid = f"dummy:{pos.value}:{idx}"
            paths[pid] = materialize_intrinsic_v1_forecast_path(
                player_id=pid, position=pos, evaluation_as_of=now,
                base_distribution=__import__("fsffl.forecast.models", fromlist=["ForecastDistribution"]).ForecastDistribution(mean=0.0, stddev=0.0),
                base_forecast_model_version="shadow-live",
            )
    return paths


def main() -> None:
    out = Path("artifacts/qb-career-state-current-shadows")
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    state = _state(now)
    live = build_current_live_forecasts(state, minimum_independent_sources=2)
    means = {obs.player_id: obs.distribution.mean for obs in live.fantasy_point_forecasts}
    pcts = rank_percentiles(means)
    player_by_id = {p.player_id: p for p in state.players}
    state_by_id = {p.player_id: p for p in state.player_states}
    id_by_name = {p.full_name: p.player_id for p in state.players}

    before_paths = _dummy_paths(live.evaluation_as_of, False)
    after_paths = _dummy_paths(live.evaluation_as_of, True)
    qbstates = {}
    for pid, y1 in means.items():
        player = player_by_id[pid]
        career = forecast_qb_career_state_runtime(
            player=player, player_state=state_by_id.get(pid), evaluation_season=2026,
            production_percentile=pcts[pid],
        )
        qbstates[pid] = career
        from fsffl.forecast.models import ForecastDistribution
        base = ForecastDistribution(mean=y1, stddev=0.0)
        before_paths[pid] = materialize_intrinsic_v1_forecast_path(
            player_id=pid, position=Position.QB, evaluation_as_of=live.evaluation_as_of,
            base_distribution=base, base_forecast_model_version=live.model_version,
        )
        after_paths[pid] = materialize_intrinsic_v1_forecast_path(
            player_id=pid, position=Position.QB, evaluation_as_of=live.evaluation_as_of,
            base_distribution=base, base_forecast_model_version=live.model_version,
            qb_career_state=career,
        )

    rows = []
    for category, (name, _age) in SHADOWS.items():
        pid = id_by_name.get(name)
        if pid is None or pid not in means:
            rows.append({"category": category, "player": name, "status": "NO_LIVE_Y1_FORECAST"})
            continue
        career = qbstates.get(pid)
        if career is None:
            rows.append({"category": category, "player": name, "status": "NO_VALID_CAREER_STATE_EVIDENCE", "y1": means[pid]})
            continue
        before = estimate_intrinsic_value_v1(
            player_path=before_paths[pid], all_player_paths=before_paths,
            league_id="qb-shadow", rules=_rules(),
        )
        after = estimate_intrinsic_value_v1(
            player_path=after_paths[pid], all_player_paths=after_paths,
            league_id="qb-shadow", rules=_rules(),
        )
        rows.append({
            "category": category,
            "player": name,
            "status": "OK",
            "y1_forecast": means[pid],
            "production_percentile": pcts[pid],
            "year2_starter_probability": career.year2_probability,
            "year3_starter_probability": career.year3_probability,
            "year2_expected_production": means[pid] * career.year2_probability,
            "year3_expected_production": means[pid] * career.year3_probability,
            "intrinsic_before": before.value,
            "intrinsic_after": after.value,
            "confidence_before": before.confidence.value,
            "confidence_after": after.confidence.value,
            "model_version": career.model_version,
            "evidence_version": career.evidence_version,
            "feature_cutoff_season": career.feature_cutoff_season,
        })

    payload = {
        "evaluation_as_of": live.evaluation_as_of.isoformat(),
        "successful_sources": live.successful_source_ids,
        "failed_sources": live.failed_sources,
        "live_qb_forecast_count": len(means),
        "shadow_context": "12-team QB+SUPERFLEX replacement safety context; standard 4-point passing TD scoring; non-QB dummy replacement paths held at zero for before/after comparison",
        "rows": rows,
    }
    (out / "qb_career_state_current_shadows.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    ok = [row for row in rows if row.get("status") == "OK"]
    if len(ok) < 5:
        raise SystemExit(f"insufficient representative current shadows: {len(ok)}")
    if any(not (0 <= r["year3_starter_probability"] <= r["year2_starter_probability"] <= 1) for r in ok):
        raise SystemExit("pathological current QB probability trajectory")


if __name__ == "__main__":
    main()
