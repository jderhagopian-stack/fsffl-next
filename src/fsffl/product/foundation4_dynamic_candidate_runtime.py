"""Run the accepted Foundation 4 dynamic-candidate materializer in the host.

The fitted route/development inputs are mounted as an existing accepted bundle;
this adapter consumes them but never downloads, fits, or rewrites model inputs.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from fsffl.forecast.long_horizon_contract import LongHorizonPolicyForecast
from fsffl.value.career_tail import CareerTailAuthority

from .dynamic_career_composition import DynamicCareerComponents


_BUNDLE_KEYS = (
    "development-module", "route-module", "model-a-rows", "qb-results",
    "raw-seasons", "players", "residual-states", "innovation-states",
    "reference-board", "current-route", "cell-metrics", "policy-freeze",
)
_MANIFEST_ENV = "FSFFL_FOUNDATION4_DYNAMIC_MATERIALIZER_MANIFEST"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    if not fields:
        raise ValueError("Foundation 4 runtime input rows are empty")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _roster_inputs(context, candidate_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    state = context.league_state
    assert state is not None
    players = {row.player_id: row for row in state.players}
    player_states = {row.player_id: row for row in state.player_states}
    roster_by_id = {
        entry.player_id: (team_state.team_id, entry.slot.value)
        for team_state in state.team_states
        for entry in team_state.roster
    }
    rows = []
    for player_id in candidate_ids:
        player = players.get(player_id)
        player_state = player_states.get(player_id)
        roster = roster_by_id.get(player_id)
        if player is None or player_state is None or player_state.age_years is None or roster is None:
            raise ValueError(f"exact-State materializer identity/age/roster missing for {player_id}")
        rows.append({
            "state_hash": state.state_id,
            "player_id": player_id,
            "position": player.position.value,
            "team_id": roster[0],
            "roster_slot": roster[1],
            "age": float(player_state.age_years),
            "state_as_of": state.as_of.isoformat(),
        })
    return rows


def materialize_foundation4_dynamic_candidates(context, live, candidate_ids):
    """Invoke the existing accepted materializer for exactly the ready roster IDs."""
    manifest_path = os.getenv(_MANIFEST_ENV, "").strip()
    if not manifest_path:
        raise ValueError(
            f"required accepted materializer input manifest is not configured: {_MANIFEST_ENV}; "
            "the manifest must name the existing development/route modules, model-A/QB "
            "inputs, raw historical seasons, player/residual/innovation panels, frozen "
            "reference board, current-route table, cell metrics, and policy freeze"
        )
    manifest_file = Path(manifest_path)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    missing = [key for key in _BUNDLE_KEYS if not str(manifest.get(key, "")).strip()]
    if missing:
        raise ValueError("accepted Foundation 4 materializer manifest missing keys: " + ", ".join(missing))
    absent = [key for key in _BUNDLE_KEYS if not Path(str(manifest[key])).is_file()]
    if absent:
        raise ValueError("accepted Foundation 4 materializer input files unavailable: " + ", ".join(absent))
    state = context.league_state
    if state is None:
        raise ValueError("Foundation 4 dynamic materialization requires exact State")
    future = live.future
    if future is None:
        raise ValueError("accepted P0 Y2/Y3 FutureForecastContract is unavailable")
    candidate_rows = []
    forecasts = {
        (row.player_id, int(row.year_index)): row
        for row in future.contract.forecasts
        if row.player_id in candidate_ids
    }
    roster_rows = {row["player_id"]: row for row in _roster_inputs(context, candidate_ids)}
    for player_id in candidate_ids:
        source = live.candidate_source_rows[player_id]
        y2, y3 = forecasts.get((player_id, 2)), forecasts.get((player_id, 3))
        if y2 is None or y3 is None:
            raise ValueError(f"accepted P0 Y2/Y3 rows missing for {player_id}")
        roster = roster_rows[player_id]
        candidate_rows.append({
            **roster,
            "historical_gsis_id": source.historical_gsis_id or "",
            "experience": source.experience,
            "league_y1_points": source.connected_league_y1_points,
            "y2_player_league_expected_points": y2.central_expectation,
            "y3_player_league_expected_points": y3.central_expectation,
            "evaluation_as_of": live.evaluation_as_of.isoformat(),
            "forecast_as_of": live.evaluation_as_of.isoformat(),
            "identity_as_of": live.evaluation_as_of.isoformat(),
            "evidence_source": "accepted-p0-live-rostered-candidate",
            "evidence_version": future.contract.forecast_model_version,
            "scoring_coordinate": future.contract.scoring_coordinate,
        })

    script = Path(__file__).resolve().parents[3] / "scripts" / "materialize_foundation4_dynamic_candidates.py"
    with tempfile.TemporaryDirectory(prefix="career405-foundation4-") as temporary:
        root = Path(temporary)
        candidate_path, roster_path, rules_path = root / "candidate.csv", root / "roster.csv", root / "rules.json"
        _write_csv(candidate_path, candidate_rows)
        _write_csv(roster_path, list(roster_rows.values()))
        rules_path.write_text(json.dumps(state.league.rules.model_dump(mode="json")), encoding="utf-8")
        command = [sys.executable, str(script)]
        for key in _BUNDLE_KEYS:
            command.extend(("--" + key, str(manifest[key])))
        command.extend(("--connected-rules", str(rules_path), "--candidate-input", str(candidate_path),
                        "--state-roster", str(roster_path), "--out-dir", str(root / "out")))
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode:
            detail = (completed.stderr or completed.stdout).strip()[-1200:]
            raise RuntimeError(f"accepted Foundation 4 materializer exit={completed.returncode}: {detail}")
        output = root / "out"
        with (output / "FOUNDATION4_DYNAMIC_CANDIDATE_Y4_Y7.csv").open(newline="", encoding="utf-8") as handle:
            y4_rows = list(csv.DictReader(handle))
        by_player: dict[str, list[LongHorizonPolicyForecast]] = {}
        for row in y4_rows:
            typed = LongHorizonPolicyForecast.model_validate(row)
            by_player.setdefault(typed.player_id, []).append(typed)
        tail_payload = json.loads((output / "FOUNDATION4_DYNAMIC_CANDIDATE_Y8_PLUS_AUTHORITY.json").read_text(encoding="utf-8"))
        tails = {str(row["player_id"]): CareerTailAuthority.model_validate(row) for row in tail_payload}
    return DynamicCareerComponents(
        y4_y7={key: tuple(value) for key, value in by_player.items()},
        y8_plus=tails,
        failures={},
    )
