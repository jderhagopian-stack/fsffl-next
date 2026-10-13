"""Run the accepted Foundation 4 dynamic-candidate materializer in the host.

The fitted route/development inputs are mounted as an existing accepted bundle;
this adapter consumes them but never downloads, fits, or rewrites model inputs.
"""
from __future__ import annotations

import csv
import gc
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from fsffl.forecast.long_horizon_contract import LongHorizonPolicyForecast
from fsffl.forecast.future_contract import CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
from fsffl.value.career_tail import CareerTailAuthority

from .dynamic_career_composition import DynamicCareerComponents


_BUNDLE_KEYS = (
    "development-module", "route-module", "model-a-rows", "qb-results",
    "raw-seasons", "players", "residual-states", "innovation-states",
    "reference-board", "current-route", "cell-metrics", "policy-freeze",
)
_MANIFEST_ENV = "FSFFL_FOUNDATION4_DYNAMIC_MATERIALIZER_MANIFEST"
_BUNDLE_ROOT_ENV = "FSFFL_FOUNDATION4_DYNAMIC_MATERIALIZER_ROOT"
_BUNDLE_MANIFEST_NAME = "foundation4_dynamic_materializer_manifest.json"


def _accepted_materializer_manifest() -> tuple[dict[str, Any], Path]:
    """Resolve the mounted accepted-input bundle used by the hosted route.

    Deployments may mount an immutable bundle directory, rather than setting a
    path to its manifest file. Keep the legacy manifest setting supported, but
    make the runtime-root handoff explicit and deterministic for normal hosts.
    """
    manifest_path = os.getenv(_MANIFEST_ENV, "").strip()
    if manifest_path:
        path = Path(manifest_path)
    else:
        bundle_root = os.getenv(_BUNDLE_ROOT_ENV, "").strip()
        if not bundle_root:
            raise ValueError(
                "accepted Foundation 4 materializer bundle is not configured: set "
                f"{_BUNDLE_ROOT_ENV} to the mounted immutable bundle or {_MANIFEST_ENV} "
                "to its manifest"
            )
        path = Path(bundle_root) / _BUNDLE_MANIFEST_NAME
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"accepted Foundation 4 materializer manifest unavailable or invalid: {path}"
        ) from exc
    if not isinstance(manifest, dict):
        raise ValueError("accepted Foundation 4 materializer manifest must be a JSON object")
    return manifest, path


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    if not fields:
        raise ValueError("Foundation 4 runtime input rows are empty")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_candidate_failures(path: Path, failures: dict[str, str], live) -> None:
    """Persist explicit player failures for the materializer's roster checkpoint."""
    source_failures = getattr(live, "failures", {})
    failures = {**source_failures, **failures}
    rows = []
    for player_id, detail in sorted(failures.items()):
        source_detail = source_failures.get(player_id)
        rows.append({
            "player_id": player_id,
            "failure_code": "p0_input_incomplete",
            "failure_detail": str(source_detail or detail),
            "evidence_checked": json.dumps(
                ["accepted_p0_year1", "accepted_p0_y2_y3", "exact_state_roster"],
                separators=(",", ":"),
            ),
            "provenance": json.dumps({
                "evaluation_as_of": live.evaluation_as_of.isoformat(),
                "future_forecast_model_version": live.future.contract.forecast_model_version,
                "scoring_coordinate": live.future.contract.scoring_coordinate,
            }, sort_keys=True, separators=(",", ":")),
        })
    fields = ("player_id", "failure_code", "failure_detail", "evidence_checked", "provenance")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _run_materializer_in_process(script: Path, arguments: list[str]) -> None:
    """Run the existing batch scorer in the hosted process, avoiding a second RSS baseline."""
    module_name = "fsffl_foundation4_dynamic_materializer_runtime"
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"accepted Foundation 4 materializer script is unavailable: {script}")
    module = importlib.util.module_from_spec(spec)
    previous_argv = sys.argv
    try:
        sys.argv = [str(script), *arguments]
        spec.loader.exec_module(module)
        module.main()
    finally:
        sys.argv = previous_argv
        sys.modules.pop(module_name, None)
        del module
        gc.collect()


def _roster_input(context, player_id: str) -> dict[str, Any]:
    state = context.league_state
    assert state is not None
    players = {row.player_id: row for row in state.players}
    player_states = {row.player_id: row for row in state.player_states}
    roster_by_id = {
        entry.player_id: (team_state.team_id, entry.slot.value)
        for team_state in state.team_states
        for entry in team_state.roster
    }
    player = players.get(player_id)
    player_state = player_states.get(player_id)
    roster = roster_by_id.get(player_id)
    if player is None or roster is None:
        raise ValueError(f"exact-State materializer identity/roster missing for {player_id}")
    return {
        "state_hash": state.state_id,
        "player_id": player_id,
        "position": player.position.value,
        "team_id": roster[0],
        "roster_slot": roster[1],
        "age": float(player_state.age_years) if player_state and player_state.age_years is not None else None,
        "state_as_of": state.as_of.isoformat(),
    }


def _roster_inputs(context, candidate_ids: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    if candidate_ids is None:
        state = context.league_state
        assert state is not None
        supported = {
            player.player_id for player in state.players
            if player.position.value in {"QB", "RB", "WR", "TE"}
        }
        candidate_ids = tuple(sorted(
            entry.player_id
            for team in state.team_states
            for entry in team.roster
            if entry.player_id in supported
        ))
    return [_roster_input(context, player_id) for player_id in candidate_ids]


def _candidate_rows(context, live, candidate_ids: tuple[str, ...], forecasts):
    """Build valid materializer inputs independently; retain bad IDs as failures."""
    rows: list[dict[str, Any]] = []
    failures: dict[str, str] = {}
    future = live.future
    assert future is not None
    for player_id in candidate_ids:
        try:
            source = live.candidate_source_rows[player_id]
            y2, y3 = forecasts.get((player_id, 2)), forecasts.get((player_id, 3))
            if y2 is None or y3 is None:
                raise ValueError("accepted P0 Y2/Y3 FutureForecastContract rows missing")
            roster = _roster_input(context, player_id)
            rows.append({
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
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            failures[player_id] = f"dynamic candidate inputs invalid: {type(exc).__name__}: {exc}"
    return rows, failures


def materialize_foundation4_dynamic_candidates(context, live, candidate_ids):
    """Invoke the existing accepted materializer for exactly the ready roster IDs."""
    manifest, manifest_file = _accepted_materializer_manifest()
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
    if future.contract.scoring_coordinate != CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE:
        raise ValueError("accepted P0 Y2/Y3 scoring coordinate differs from Foundation 4 FSFFL")
    forecasts = {
        (row.player_id, int(row.year_index)): row
        for row in future.contract.forecasts
        if row.player_id in candidate_ids
    }
    candidate_rows, failures = _candidate_rows(context, live, tuple(candidate_ids), forecasts)
    if not candidate_rows:
        return DynamicCareerComponents(y4_y7={}, y8_plus={}, failures=failures)
    candidate_ids = tuple(row["player_id"] for row in candidate_rows)
    # Full exact-State roster is needed for the materializer's Position & Depth
    # response and durable accounting; candidate inputs remain limited to the
    # explicitly selected dynamic cohort.
    roster_rows = {
        row["player_id"]: row
        for row in _roster_inputs(context)
    }

    script = Path(__file__).resolve().parents[3] / "scripts" / "materialize_foundation4_dynamic_candidates.py"
    with tempfile.TemporaryDirectory(prefix="career405-foundation4-") as temporary:
        root = Path(temporary)
        candidate_path, roster_path = root / "candidate.csv", root / "roster.csv"
        rules_path, failures_path = root / "rules.json", root / "candidate-failures.csv"
        _write_csv(candidate_path, candidate_rows)
        _write_csv(roster_path, list(roster_rows.values()))
        _write_candidate_failures(failures_path, failures, live)
        rules_path.write_text(json.dumps(state.league.rules.model_dump(mode="json")), encoding="utf-8")
        arguments: list[str] = []
        for key in _BUNDLE_KEYS:
            arguments.extend(("--" + key, str(manifest[key])))
        arguments.extend((
            "--connected-rules", str(rules_path), "--candidate-input", str(candidate_path),
            "--state-roster", str(roster_path), "--candidate-failures", str(failures_path),
            "--evaluation-as-of", live.evaluation_as_of.isoformat(),
            "--durable-roster-checkpoint", str(root / "private" / "roster-checkpoint.json"),
            "--out-dir", str(root / "out"),
        ))
        _run_materializer_in_process(script, arguments)
        output = root / "out"
        with (output / "FOUNDATION4_DYNAMIC_CANDIDATE_Y4_Y7.csv").open(newline="", encoding="utf-8") as handle:
            y4_rows = list(csv.DictReader(handle))
        by_player: dict[str, list[LongHorizonPolicyForecast]] = {}
        for row in y4_rows:
            # The materializer CSV intentionally carries exact-State provenance
            # columns beside the typed Forecast contract. Only parse the fields
            # owned by LongHorizonPolicyForecast (which forbids extras).
            parsed = {
                key: row[key]
                for key in LongHorizonPolicyForecast.model_fields
                if key in row
            }
            for field in ("evaluation_season", "year_index", "target_season"):
                parsed[field] = int(parsed[field])
            for field in ("central_expectation", "absolute_error_80", "absolute_error_90"):
                parsed[field] = float(parsed[field])
            typed = LongHorizonPolicyForecast.model_validate(parsed)
            by_player.setdefault(typed.player_id, []).append(typed)
        tail_payload = json.loads((output / "FOUNDATION4_DYNAMIC_CANDIDATE_Y8_PLUS_AUTHORITY.json").read_text(encoding="utf-8"))
        tails = {str(row["player_id"]): CareerTailAuthority.model_validate(row) for row in tail_payload}
    return DynamicCareerComponents(
        y4_y7={key: tuple(value) for key, value in by_player.items()},
        y8_plus=tails,
        failures=failures,
    )
