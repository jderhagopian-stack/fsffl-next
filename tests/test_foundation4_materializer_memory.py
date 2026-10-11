from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from scripts.materialize_foundation4_current_long_horizon_board import (
    build_history_inputs_memory_bounded,
)


class TinyDevelopment:
    """Small deterministic stand-in for the frozen route's DataFrame transforms."""

    def add_qb_governed_path(self, model_a: pd.DataFrame, qb_results: dict) -> pd.DataFrame:
        result = model_a.copy()
        result["qb_adjustment"] = result["player_id"].map(qb_results).fillna(0.0)
        return result

    def build_forecast_base(self, model_a: pd.DataFrame) -> pd.DataFrame:
        result = model_a.copy()
        result["base_value"] = result["model_value"] + result["qb_adjustment"]
        return result[["player_id", "base_value"]]

    def prep_raw(self, raw: pd.DataFrame) -> pd.DataFrame:
        return raw.sort_values("player_id").reset_index(drop=True)

    def merge_lags(self, base: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
        return base.merge(raw[["player_id", "lag_value"]], on="player_id", validate="one_to_one")

    def add_engineered_features(
        self, base: pd.DataFrame, players: pd.DataFrame
    ) -> pd.DataFrame:
        return base.merge(players[["player_id", "feature_value"]], on="player_id", validate="one_to_one")

    def merge_trajectory(
        self, base: pd.DataFrame, residual: pd.DataFrame, innovation: pd.DataFrame
    ) -> pd.DataFrame:
        result = base.merge(residual, on="player_id", validate="one_to_one")
        return result.merge(innovation, on="player_id", validate="one_to_one")

    def build_long(self, base: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
        return base.merge(raw[["player_id", "target_value"]], on="player_id", validate="one_to_one")


def _write_frame(path: Path, rows: list[dict]) -> str:
    pd.DataFrame(rows).to_csv(path, index=False)
    return str(path)


def _legacy_build_inputs(dev: TinyDevelopment, args: SimpleNamespace) -> pd.DataFrame:
    model_a = pd.read_csv(args.model_a_rows)
    qb_results = json.loads(Path(args.qb_results).read_text())
    raw = dev.prep_raw(pd.read_csv(args.raw_seasons))
    players = pd.read_csv(args.players)
    residual = pd.read_csv(args.residual_states)
    innovation = pd.read_csv(args.innovation_states)
    model_a = dev.add_qb_governed_path(model_a, qb_results)
    base = dev.build_forecast_base(model_a)
    base = dev.merge_lags(base, raw)
    base = dev.add_engineered_features(base, players)
    base = dev.merge_trajectory(base, residual, innovation)
    return dev.build_long(base, raw)


def test_memory_bounded_history_builder_matches_frozen_route_input_rows(tmp_path):
    model_a = _write_frame(tmp_path / "model.csv", [
        {"player_id": "p2", "model_value": 20.0},
        {"player_id": "p1", "model_value": 10.0},
    ])
    raw = _write_frame(tmp_path / "raw.csv", [
        {"player_id": "p1", "lag_value": 1.0, "target_value": 101.0},
        {"player_id": "p2", "lag_value": 2.0, "target_value": 202.0},
    ])
    players = _write_frame(tmp_path / "players.csv", [
        {"player_id": "p1", "feature_value": 11.0},
        {"player_id": "p2", "feature_value": 22.0},
    ])
    residual = _write_frame(tmp_path / "residual.csv", [
        {"player_id": "p1", "residual_value": 0.1},
        {"player_id": "p2", "residual_value": 0.2},
    ])
    innovation = _write_frame(tmp_path / "innovation.csv", [
        {"player_id": "p1", "innovation_value": 1.1},
        {"player_id": "p2", "innovation_value": 1.2},
    ])
    qb_results = tmp_path / "qb.json"
    qb_results.write_text(json.dumps({"p1": 0.5, "p2": -0.5}))
    args = SimpleNamespace(
        model_a_rows=model_a,
        qb_results=qb_results,
        raw_seasons=raw,
        players=players,
        residual_states=residual,
        innovation_states=innovation,
    )
    dev = TinyDevelopment()

    expected = _legacy_build_inputs(dev, args)
    actual = build_history_inputs_memory_bounded(dev, args)

    pd.testing.assert_frame_equal(actual, expected)
