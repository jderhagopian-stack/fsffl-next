from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd


EXPECTED_PACKAGE_SHA256 = "ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7"
EXPECTED_PANEL_SHA256 = "c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7"
EXPECTED_IDENTITY_ROWS_SHA256 = "1803ee0200b8d1d39dfd719934bd683765727bef997f2a1f1ee44d2a6444af56"
EXPECTED_LEAGUE_BOARD_SHA256 = "6bded35221a501471df60de8c05a6e691428552f23abb3f0cf799218fd71bfae"
EXPECTED_STANDARD_BOARD_SHA256 = "dfe817909dc42782ef4f1249692a9ad9139b5fa25311549ae741970c4ef9efe9"
EXPECTED_RAW_ARRAY_SHA256 = "4dd1fa70b9b4f886ad103a2f5b6f45f7c4f123a571f84b7a4400b0004271639d"
EXPECTED_BRIDGE = {
    "QB": 1.04575952979839,
    "RB": 1.11430683937932,
    "WR": 1.2899047488253,
    "TE": 1.35877076106381,
}
SENTINELS = (
    "Aaron Rodgers",
    "Sam Darnold",
    "Bijan Robinson",
    "Jahmyr Gibbs",
    "Puka Nacua",
    "Christian McCaffrey",
    "Brock Bowers",
    "Trey McBride",
)
POSITIVE_STATES = ("depth", "usable", "starter", "premium", "elite")
STATES = ("out",) + POSITIVE_STATES


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    tokens = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    while tokens and tokens[-1] in {"jr", "sr", "ii", "iii", "iv", "v"}:
        tokens.pop()
    return "".join(tokens)


def sleeper_id(player_id: str) -> str:
    value = str(player_id)
    for prefix in ("sleeper:player:", "diag:sleeper:", "sleeper:"):
        if value.startswith(prefix):
            external = value[len(prefix) :]
            if external:
                return f"sleeper:{external}"
    raise RuntimeError(f"unsupported player id: {player_id}")


def current_state(points: float, thresholds: list[float]) -> str:
    if points <= 0:
        return "out"
    index = 0
    while index < len(thresholds) and points > thresholds[index]:
        index += 1
    return POSITIVE_STATES[index]


def derive_experience_2026(
    gsis_id: str | None,
    panel: pd.DataFrame,
    roster_fallback: set[str],
) -> tuple[int, str]:
    if not gsis_id:
        return 0, "UNMATCHED_COLD_START"
    history = panel[panel.player_id.astype(str) == str(gsis_id)]
    if len(history):
        entry = pd.to_numeric(history.entry_season_used, errors="coerce").dropna()
        if len(entry):
            return max(0, 2026 - int(entry.iloc[-1])), "PHASE2_ENTRY_SEASON"
        latest = history.sort_values("season").iloc[-1]
        return (
            max(0, int(latest.experience_years) + (2026 - int(latest.season))),
            "PHASE2_ELAPSED_FROM_LATEST",
        )
    if str(gsis_id) in roster_fallback:
        return 1, "APPROVED_2025_ROSTER_FIRST_OBSERVED_FALLBACK"
    raise RuntimeError(f"no governed experience source for mapped identity {gsis_id}")


def career_stage(experience: int) -> str:
    if experience <= 3:
        return "developmental"
    if experience <= 8:
        return "established"
    return "veteran"


def coarse_age_band(position: str, age: float) -> str:
    if position == "QB":
        if age <= 25:
            return "young"
        if age <= 31:
            return "prime"
        return "aging"
    if age <= 22:
        return "young"
    if age <= 27:
        return "prime"
    return "aging"


def verify_inputs(args: argparse.Namespace) -> dict:
    package_sha = sha256_file(args.package)
    panel_sha = sha256_file(args.panel)
    if package_sha != EXPECTED_PACKAGE_SHA256:
        raise RuntimeError(f"P0 package hash mismatch: {package_sha}")
    if panel_sha != EXPECTED_PANEL_SHA256:
        raise RuntimeError(f"Phase-2 panel hash mismatch: {panel_sha}")

    league = load_json(args.league_y1)
    standard = load_json(args.standard_y1)
    identity = load_json(args.identity_coordinate)
    if league.get("board_sha256") != EXPECTED_LEAGUE_BOARD_SHA256:
        raise RuntimeError("preserved league Year-1 board hash mismatch")
    if standard.get("board_sha256") != EXPECTED_STANDARD_BOARD_SHA256:
        raise RuntimeError("preserved standard Year-1 board hash mismatch")
    if identity.get("rows_sha256") != EXPECTED_IDENTITY_ROWS_SHA256:
        raise RuntimeError("replacement identity row-material hash mismatch")
    if len(league.get("rows", [])) != 335 or len(standard.get("rows", [])) != 335:
        raise RuntimeError("preserved Year-1 boards must contain 335 rows")
    league_ids = {sleeper_id(row["player_id"]) for row in league["rows"]}
    standard_ids = {sleeper_id(row["player_id"]) for row in standard["rows"]}
    if league_ids != standard_ids or len(league_ids) != 335:
        raise RuntimeError("preserved Year-1 league/standard identity parity failed")
    if "sleeper:8800" not in league_ids or "sleeper:11630" in league_ids:
        raise RuntimeError("preserved preseason population is not authoritative")

    return {
        "package_sha256": package_sha,
        "panel_sha256": panel_sha,
        "league_y1_file_sha256": sha256_file(args.league_y1),
        "league_y1_board_sha256": league["board_sha256"],
        "standard_y1_file_sha256": sha256_file(args.standard_y1),
        "standard_y1_board_sha256": standard["board_sha256"],
        "raw_array_sha256": EXPECTED_RAW_ARRAY_SHA256,
        "identity_coordinate_file_sha256": sha256_file(args.identity_coordinate),
        "identity_rows_sha256": identity["rows_sha256"],
        "old_live_y1_file_sha256": sha256_file(args.old_live_y1),
        "provider_snapshot_file_sha256": sha256_file(args.provider_snapshot),
        "nflverse_players_file_sha256": sha256_file(args.nflverse_players),
        "history_file_sha256": sha256_file(args.history),
        "age_completion_file_sha256": sha256_file(args.age_completion),
        "boundaries_file_sha256": sha256_file(args.boundaries),
        "materializer_file_sha256": sha256_file(Path(__file__)),
    }


def build_source(args: argparse.Namespace) -> tuple[pd.DataFrame, dict]:
    standard = load_json(args.standard_y1)
    league = load_json(args.league_y1)
    old_y1 = load_json(args.old_live_y1)
    identity = load_json(args.identity_coordinate)
    provider = load_json(args.provider_snapshot)
    boundaries = load_json(args.boundaries)["boundaries"]
    panel = pd.read_csv(args.panel, dtype={"player_id": str})
    history = pd.read_csv(args.history, dtype={"gsis_id": str})
    nflverse = pd.read_csv(args.nflverse_players, dtype=str, low_memory=False)

    league_by_id = {sleeper_id(row["player_id"]): row for row in league["rows"]}
    old_y1_by_id = {sleeper_id(row["completed_source_player_id"]): row for row in old_y1["rows"]}
    old_identity_by_id = {str(row["current_player_id"]): row for row in identity["rows"]}
    provider_rows = list(provider["rows"])
    history_idx = history.set_index("gsis_id", drop=False)
    roster_fallback = {"00-0040177", "00-0040203"}

    records: list[dict] = []
    added_mapping: dict | None = None
    for row in standard["rows"]:
        current_id = sleeper_id(row["player_id"])
        name = str(row["full_name"])
        position = str(row["position"])
        if current_id in old_identity_by_id:
            mapping = old_identity_by_id[current_id]
            old_row = old_y1_by_id[current_id]
            if mapping["player_name"] != name or mapping["position"] != position:
                raise RuntimeError(f"shared identity mismatch for {current_id}")
            age = float(old_row["player_state"]["age_years"])
        else:
            normalized = normalize_name(name)
            candidates = [
                candidate
                for candidate in provider_rows
                if candidate["position"] == position
                and normalized in set(candidate.get("normalized_aliases", []))
            ]
            if len(candidates) != 1:
                raise RuntimeError(
                    f"preseason-only identity did not have one governed name+position match: "
                    f"{name}/{position} -> {len(candidates)}"
                )
            candidate = candidates[0]
            gsis_id = str(candidate["gsis_id"])
            nfl_row = nflverse[nflverse.gsis_id.astype(str) == gsis_id]
            if len(nfl_row) != 1 or pd.isna(nfl_row.iloc[0].birth_date):
                raise RuntimeError(f"missing governed DOB for {name}/{gsis_id}")
            born = date.fromisoformat(str(nfl_row.iloc[0].birth_date))
            age = (date(2026, 9, 1) - born).days / 365.2425
            mapping = {
                "current_player_id": current_id,
                "player_name": name,
                "position": position,
                "historical_gsis_id": gsis_id,
                "mapping_status": "EXACT_NAME_POSITION",
                "mapping_method": "EXACT_NAME_POSITION",
                "identity_snapshot_coordinate": provider["coordinate_id"],
                "age_source": "governed_nflverse_DOB_frozen_A2_rule",
            }
            added_mapping = mapping | {"age_years": age, "date_of_birth": str(born)}

        gsis_id = mapping.get("historical_gsis_id")
        gsis_id = None if gsis_id is None else str(gsis_id)
        experience, experience_source = derive_experience_2026(gsis_id, panel, roster_fallback)
        hrow = None
        if gsis_id and gsis_id in history_idx.index:
            hrow = history_idx.loc[gsis_id]
            if isinstance(hrow, pd.DataFrame):
                hrow = hrow[hrow.position.astype(str) == position]
                if len(hrow) != 1:
                    raise RuntimeError(f"ambiguous governed current history for {gsis_id}/{position}")
                hrow = hrow.iloc[0]

        prior1_coverage = int(hrow is not None)
        prior1_points = float(hrow.points_2025) if hrow is not None else np.nan
        prior_age_z = (
            float(hrow.age_state_z_2025)
            if hrow is not None and pd.notna(hrow.age_state_z_2025)
            else np.nan
        )
        prior2_coverage = int(
            hrow is not None
            and pd.notna(hrow.age_state_z_2025)
            and pd.notna(hrow.age_state_z_2024)
        )
        prior2_mean = (
            float((float(hrow.age_state_z_2025) + float(hrow.age_state_z_2024)) / 2)
            if prior2_coverage
            else np.nan
        )
        prior2_gap = (
            float(abs(float(hrow.age_state_z_2025) - float(hrow.age_state_z_2024)))
            if prior2_coverage
            else np.nan
        )
        y1_points = float(row["mean"])
        records.append(
            {
                "player_id": str(row["player_id"]),
                "current_player_id": current_id,
                "player_name": name,
                "position": position,
                "age": float(age),
                "experience": int(experience),
                "experience_source": experience_source,
                "career_stage": career_stage(experience),
                "age_band": coarse_age_band(position, float(age)),
                "mapping_status": str(mapping["mapping_status"]),
                "historical_gsis_id": gsis_id,
                "history_status": (
                    "MAPPED_2025"
                    if hrow is not None
                    else (
                        "UNMATCHED_COLD_START"
                        if mapping["mapping_status"] == "UNMATCHED"
                        else "MAPPED_NO_2025_ROW"
                    )
                ),
                "y1_points": y1_points,
                "league_y1_points": float(league_by_id[current_id]["mean"]),
                "source_state": current_state(y1_points, boundaries[position]["thresholds"]),
                "prior1_points": prior1_points,
                "prior1_coverage": prior1_coverage,
                "source_role_band": str(hrow.role_band_2025) if hrow is not None else "unknown",
                "games": float(hrow.games_2025) if hrow is not None else np.nan,
                "opportunity_per_game": (
                    float(hrow.opportunity_per_game_2025) if hrow is not None else np.nan
                ),
                "prior_age_state_resid_z": prior_age_z,
                "prior2_coverage": prior2_coverage,
                "prior2_mean_age_state_z": prior2_mean,
                "prior2_gap_age_state_z": prior2_gap,
            }
        )

    source = pd.DataFrame(records)
    if len(source) != 335 or source.player_id.nunique() != 335:
        raise RuntimeError("reconciled preseason source is not 335 unique players")
    old_ids = set(old_identity_by_id)
    new_ids = set(source.current_player_id)
    if old_ids & new_ids != new_ids - {"sleeper:8800"}:
        raise RuntimeError("shared-population reconciliation is not exactly 334 players")
    if old_ids - new_ids != {"sleeper:11630"} or new_ids - old_ids != {"sleeper:8800"}:
        raise RuntimeError("population delta is not Roman Wilson -> Malik Davis")
    if added_mapping is None or added_mapping["historical_gsis_id"] != "00-0037563":
        raise RuntimeError("Malik Davis did not resolve to the governed history mapping")

    source["source_percentile"] = np.nan
    source["state_percentile"] = np.nan
    for _, indexes in source.groupby("position").groups.items():
        values = source.loc[indexes, "y1_points"]
        source.loc[indexes, "source_percentile"] = (values.rank(method="average") - 0.5) / len(values)
    for _, indexes in source.groupby(["position", "source_state"]).groups.items():
        values = source.loc[indexes, "y1_points"]
        source.loc[indexes, "state_percentile"] = (values.rank(method="average") - 0.5) / len(values)

    bridge = {}
    for position, group in source.groupby("position"):
        denominator = float(group.y1_points.clip(lower=0).sum())
        numerator = float(group.league_y1_points.clip(lower=0).sum())
        multiplier = numerator / denominator
        if abs(multiplier - EXPECTED_BRIDGE[position]) > 1e-12:
            raise RuntimeError(
                f"governed standard-to-league bridge drift for {position}: {multiplier}"
            )
        bridge[position] = multiplier

    reconciliation = {
        "shared_players": 334,
        "preseason_only": added_mapping,
        "old_live_only": {
            "current_player_id": "sleeper:11630",
            "player_name": old_identity_by_id["sleeper:11630"]["player_name"],
            "position": old_identity_by_id["sleeper:11630"]["position"],
        },
        "preseason_position_counts": {
            key: int(value) for key, value in source.position.value_counts().sort_index().items()
        },
        "standard_to_league_bridge": bridge,
        "bridge_application_count_for_future_outputs": 1,
    }
    return source, reconciliation


def materialize(source: pd.DataFrame, package: dict, dfv: object, bridge: dict[str, float]) -> pd.DataFrame:
    outputs: list[dict] = []
    for source_row in source.sort_values("player_id").itertuples(index=False):
        output = {
            "player_id": source_row.player_id,
            "current_player_id": source_row.current_player_id,
            "player_name": source_row.player_name,
            "position": source_row.position,
            "historical_gsis_id": source_row.historical_gsis_id,
            "age": float(source_row.age),
            "experience": int(source_row.experience),
            "career_stage": source_row.career_stage,
            "age_band": source_row.age_band,
            "mapping_status": source_row.mapping_status,
            "history_status": source_row.history_status,
            "experience_source": source_row.experience_source,
            "source_state": source_row.source_state,
            "source_percentile": float(source_row.source_percentile),
            "state_percentile": float(source_row.state_percentile),
            "standard_y1_points": float(source_row.y1_points),
            "league_y1_points": float(source_row.league_y1_points),
            "prior1_coverage": int(source_row.prior1_coverage),
            "prior2_coverage": int(source_row.prior2_coverage),
            "league_bridge_multiplier": float(bridge[source_row.position]),
        }
        for horizon in (2, 3):
            horizon_package = package["horizons"][str(horizon)]
            row = SimpleNamespace(
                **source_row._asdict(),
                horizon=horizon,
                source_points=float(source_row.y1_points),
            )
            layer = (
                horizon_package["state_qb"]
                if source_row.position == "QB"
                else horizon_package["state_nonqb"]
            )
            probabilities = dfv.score_prob(layer, row)
            route_cell = f"{source_row.position}|{source_row.career_stage}"
            route = package["selection"][str(horizon)]["selected_route"][route_cell]
            model = horizon_package["production_models"][route]
            if route == "D0":
                conditional = float(dfv.score_prod(model, row))
                state_means = {state: conditional for state in POSITIVE_STATES}
                expected = (1 - probabilities["out"]) * conditional
            else:
                state_means = {
                    state: float(dfv.score_prod(model, row, state))
                    for state in POSITIVE_STATES
                }
                expected = sum(probabilities[state] * state_means[state] for state in POSITIVE_STATES)
                active = 1 - probabilities["out"]
                conditional = expected / active if active > 1e-15 else 0.0
            multiplier = bridge[source_row.position]
            output.update(
                {
                    f"y{horizon}_candidate": route,
                    f"y{horizon}_route_cell": route_cell,
                    f"y{horizon}_active_probability": float(1 - probabilities["out"]),
                    f"y{horizon}_standard_conditional_active_points": float(conditional),
                    f"y{horizon}_standard_expected_points": float(expected),
                    f"y{horizon}_standard_conditional_to_y1_ratio": (
                        float(conditional / source_row.y1_points)
                        if source_row.y1_points > 0
                        else np.nan
                    ),
                    f"y{horizon}_standard_expected_to_y1_ratio": (
                        float(expected / source_row.y1_points)
                        if source_row.y1_points > 0
                        else np.nan
                    ),
                    f"y{horizon}_league_conditional_active_points": float(conditional * multiplier),
                    f"y{horizon}_league_expected_points": float(expected * multiplier),
                    f"y{horizon}_league_bridge_application_count": 1,
                }
            )
            for state in STATES:
                output[f"y{horizon}_p_{state}"] = float(probabilities[state])
            for state in POSITIVE_STATES:
                output[f"y{horizon}_standard_mean_{state}"] = float(state_means[state])
                output[f"y{horizon}_league_mean_{state}"] = float(state_means[state] * multiplier)
        outputs.append(output)
    board = pd.DataFrame(outputs)
    if len(board) != 335 or board.player_id.nunique() != 335:
        raise RuntimeError("P0 board did not materialize 335 unique players")
    probability_columns = [
        f"y{horizon}_p_{state}" for horizon in (2, 3) for state in STATES
    ]
    if not np.isfinite(board.select_dtypes(include=[np.number]).to_numpy()).all():
        raise RuntimeError("P0 board contains non-finite numeric outputs")
    for horizon in (2, 3):
        sums = board[[f"y{horizon}_p_{state}" for state in STATES]].sum(axis=1)
        if float((sums - 1.0).abs().max()) > 1e-10:
            raise RuntimeError(f"Y{horizon} state probabilities do not sum to one")
    return board


def cohort_metrics(group: pd.DataFrame) -> dict:
    result = {"n": int(len(group))}
    for horizon in (2, 3):
        active = group[f"y{horizon}_active_probability"]
        conditional = group[f"y{horizon}_standard_conditional_to_y1_ratio"]
        expected = group[f"y{horizon}_standard_expected_to_y1_ratio"]
        result[f"Y{horizon}"] = {
            "median_active_probability": float(active.median()),
            "median_conditional_to_y1_ratio": float(conditional.median()),
            "median_expected_to_y1_ratio": float(expected.median()),
            "conditional_below_60pct_share": float((conditional < 0.60).mean()),
            "conditional_below_50pct_share": float((conditional < 0.50).mean()),
        }
    return result


def inspect_persisted_board(board_path: Path) -> dict:
    board = pd.read_csv(board_path)
    top10 = board[board.source_percentile >= 0.90]
    young_top10 = top10[top10.age <= 25]
    cohorts = {
        "top10": cohort_metrics(top10),
        "young_top10": cohort_metrics(young_top10),
        "top10_by_position": {
            position: cohort_metrics(group)
            for position, group in top10.groupby("position", sort=True)
        },
    }

    age_bins = pd.cut(
        board.age,
        bins=[-np.inf, 25, 29, 33, np.inf],
        labels=["age_le25", "age_26_29", "age_30_33", "age_ge34"],
        right=True,
    )
    age_behavior = {}
    for label, group in board.groupby(age_bins, observed=False):
        age_behavior[str(label)] = {
            "n": int(len(group)),
            "Y2_median_active_probability": float(group.y2_active_probability.median()),
            "Y3_median_active_probability": float(group.y3_active_probability.median()),
            "Y3_not_above_Y2": bool(
                group.y3_active_probability.median() <= group.y2_active_probability.median()
            ),
        }

    sentinels = {}
    for name in SENTINELS:
        rows = board[board.player_name == name]
        if len(rows) != 1:
            raise RuntimeError(f"missing or ambiguous predeclared sentinel: {name}")
        row = rows.iloc[0]
        sentinels[name] = {
            "position": row.position,
            "age": float(row.age),
            "standard_Y1": float(row.standard_y1_points),
            "league_Y1": float(row.league_y1_points),
            "Y2": {
                "route": row.y2_candidate,
                "active_probability": float(row.y2_active_probability),
                "standard_conditional_active_points": float(
                    row.y2_standard_conditional_active_points
                ),
                "standard_expected_points": float(row.y2_standard_expected_points),
                "conditional_ratio": float(row.y2_standard_conditional_to_y1_ratio),
                "league_expected_points": float(row.y2_league_expected_points),
            },
            "Y3": {
                "route": row.y3_candidate,
                "active_probability": float(row.y3_active_probability),
                "standard_conditional_active_points": float(
                    row.y3_standard_conditional_active_points
                ),
                "standard_expected_points": float(row.y3_standard_expected_points),
                "conditional_ratio": float(row.y3_standard_conditional_to_y1_ratio),
                "league_expected_points": float(row.y3_league_expected_points),
            },
        }

    # Predeclared before materialization: the prior defect benchmark was universal
    # sub-60% conditional retention. PASS requires both upper-tail cohorts to have
    # median retention >=60% and no more than half of rows below 60%, at both horizons.
    pass_checks = []
    for cohort in ("top10", "young_top10"):
        for horizon in ("Y2", "Y3"):
            metrics = cohorts[cohort][horizon]
            pass_checks.append(
                metrics["median_conditional_to_y1_ratio"] >= 0.60
                and metrics["conditional_below_60pct_share"] <= 0.50
            )
    classification = (
        "PASS_FOR_MANAGEMENT_PROMOTION_REVIEW"
        if all(pass_checks)
        else "RESIDUAL_MATERIAL_SYSTEMATIC_COMPRESSION"
    )
    return {
        "classification_rule": {
            "basis": "the previously declared 60% upper-tail conditional-retention defect threshold",
            "pass": "For top10 and young_top10 at Y2 and Y3: median conditional retention >=0.60 and share below 0.60 <=0.50.",
            "post_inspection_model_changes_allowed": False,
        },
        "classification": classification,
        "cohorts": cohorts,
        "age_persistence_behavior": age_behavior,
        "sentinels": sentinels,
    }


def management_report(manifest: dict, diagnostics: dict) -> str:
    top = diagnostics["cohorts"]["top10"]
    young = diagnostics["cohorts"]["young_top10"]
    passed = diagnostics["classification"].startswith("PASS")
    return f"""# FSFFL NEXT — Corrected P0 / Preseason Credibility Gate

Date: 2026-09-19  
Outcome: **{diagnostics['classification']}**

## Executive result

The exact persisted P0 package was replayed once, without fit or tuning, over the preserved 335-player preseason standard/non-PPR Year-1 coordinate. The separate connected-league Year-1 board remains direct raw-stat scoring, and future P0 production was translated through the governed position bridge exactly once.

The prior elite-compression finding {'materially normalizes on the corrected source coordinate' if passed else 'remains materially systematic on the corrected source coordinate'}. This run therefore {'passes to management promotion review' if passed else 'stops with a residual Forecast defect'}; it does not modify PR #147 runtime authority.

## Upper-tail credibility

| Cohort | N | Y2 median active | Y2 median conditional/Y1 | Y2 below 60% | Y3 median active | Y3 median conditional/Y1 | Y3 below 60% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Top 10% | {top['n']} | {top['Y2']['median_active_probability']:.3f} | {top['Y2']['median_conditional_to_y1_ratio']:.3f} | {top['Y2']['conditional_below_60pct_share']:.1%} | {top['Y3']['median_active_probability']:.3f} | {top['Y3']['median_conditional_to_y1_ratio']:.3f} | {top['Y3']['conditional_below_60pct_share']:.1%} |
| Young top 10% | {young['n']} | {young['Y2']['median_active_probability']:.3f} | {young['Y2']['median_conditional_to_y1_ratio']:.3f} | {young['Y2']['conditional_below_60pct_share']:.1%} | {young['Y3']['median_active_probability']:.3f} | {young['Y3']['median_conditional_to_y1_ratio']:.3f} | {young['Y3']['conditional_below_60pct_share']:.1%} |

The prior wrong-coordinate board had top-10% median conditional retention of 0.452 / 0.397 (Y2/Y3) and young-top-10% retention of 0.475 / 0.431, with 100% below 60% at both horizons.

## Provenance and population

- P0 package SHA-256: `{manifest['inputs']['package_sha256']}`.
- Preserved raw ensemble: 1,675 observations; SHA-256 `{manifest['inputs']['raw_array_sha256']}`.
- Direct league Year-1 board: 335 rows; governed board SHA-256 `{manifest['inputs']['league_y1_board_sha256']}`.
- Standard/non-PPR P0 source board: 335 rows; governed board SHA-256 `{manifest['inputs']['standard_y1_board_sha256']}`.
- Complete P0 board: 335 players / 670 horizon rows; CSV SHA-256 `{manifest['outputs']['board_csv_sha256']}`.
- Population reconciliation: 334 shared players; Roman Wilson removed with the later live universe; preseason Malik Davis added by the existing exact-name/position rule and governed GSIS history `00-0037563`.

## Boundaries

No B2a/R1-R2 recovery, P0 fit/refit, coefficient or route change, feature change, training-window choice, current-player tuning, runtime Forecast change, merge, or deploy occurred. Current-player inspection began only after the complete board was persisted and hashed. STOP for management review.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in (
        "standard_y1",
        "league_y1",
        "old_live_y1",
        "identity_coordinate",
        "provider_snapshot",
        "nflverse_players",
        "history",
        "age_completion",
        "panel",
        "boundaries",
        "package",
        "module_dir",
        "outdir",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True, type=Path, dest=name)
    args = parser.parse_args()

    sys.path.insert(0, str(args.module_dir))
    dfv = importlib.import_module("deployment_fit_v1")

    inputs = verify_inputs(args)
    source, reconciliation = build_source(args)
    package = load_json(args.package)

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    board = materialize(source, package, dfv, reconciliation["standard_to_league_bridge"])
    board_path = outdir / "CORRECTED_P0_PRESEASON_BOARD_335.csv"
    board.to_csv(board_path, index=False, lineterminator="\n")
    board_sha = sha256_file(board_path)
    source_path = outdir / "RECONCILED_PRESEASON_SOURCE_335.csv"
    source.sort_values("player_id").to_csv(source_path, index=False, lineterminator="\n")

    # The board is complete and hashed before this first diagnostic read.
    diagnostics = inspect_persisted_board(board_path)
    diagnostics_path = outdir / "CREDIBILITY_DIAGNOSTICS.json"
    diagnostics_path.write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": "fsffl-corrected-p0-preseason-credibility-gate-v1",
        "date": "2026-09-19",
        "classification": diagnostics["classification"],
        "materialization": {
            "P0_package_replays": 1,
            "model_fits": 0,
            "model_refits": 0,
            "current_player_tuning_actions": 0,
            "post_board_model_changes": 0,
            "players": 335,
            "horizon_rows": 670,
        },
        "year1": {
            "raw_observations": 1675,
            "league_scoring": "direct from preserved raw observations",
            "internal_P0_coordinate": "independently direct-scored standard/non-PPR from the same raw observations",
            "multiplier_used_to_estimate_year1": False,
        },
        "population_reconciliation": reconciliation,
        "inputs": inputs,
        "outputs": {
            "board_csv": board_path.name,
            "board_csv_sha256": board_sha,
            "board_canonical_rows_sha256": canonical_json_sha256(
                board.replace({np.nan: None}).to_dict(orient="records")
            ),
            "source_csv": source_path.name,
            "source_csv_sha256": sha256_file(source_path),
            "diagnostics_json": diagnostics_path.name,
            "diagnostics_json_sha256": sha256_file(diagnostics_path),
        },
        "authority": {
            "PR147_runtime_forecast_modified": False,
            "merge": False,
            "deploy": False,
            "stop": "STOP_FOR_MANAGEMENT_REVIEW",
        },
    }
    manifest_path = outdir / "PROVENANCE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    report_path = outdir / "MANAGEMENT_REPORT.md"
    report_path.write_text(management_report(manifest, diagnostics), encoding="utf-8")
    print(
        json.dumps(
            {
                "classification": diagnostics["classification"],
                "board_sha256": board_sha,
                "manifest": str(manifest_path),
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
