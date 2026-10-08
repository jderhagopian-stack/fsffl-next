"""#405 PR1 evidence-only semantic replay. Never trains, reroutes, or relaxes board parity.

Inputs: frozen accepted board+terminal artifact, previously archived deterministic replay
board, and exact accepted historical evidence. Current Y1-Y3 comes from the existing
frozen 335 Current Shapley diagnostic, held IDENTICAL in both counterfactuals.
#370 uses a clearly marked synthetic complete-cohort State, not actual live league.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from fsffl.forecast.long_horizon_contract import (
    LongHorizonForecastAuthorityContract, LongHorizonPolicyForecast,
)
from fsffl.product.foundation4_shadow_inputs import FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING
from fsffl.state.models import (
    League, LeagueRules, LeagueState, LineupRequirement, Player, PlayerState,
    Position, Provenance, RosterEntry, RosterSlot, Team, TeamState,
)
from fsffl.value.career_forward_intrinsic import build_career_forward_intrinsic_shadow
from fsffl.value.career_tail import CareerTailFeatures, build_career_tail_authority
from fsffl.value.long_term_intrinsic import build_long_term_intrinsic_shadow
from fsffl.value.shapley_intrinsic_contract import (
    CompletedSourceFactProvenance, DiagnosticH1Evidence, ShapleyHorizonProvenance,
    ShapleyHorizonUncertainty, ShapleyIntrinsicAvailability,
    ShapleyIntrinsicContract, ShapleyIntrinsicCoverage,
    ShapleyIntrinsicHorizonContribution, ShapleyIntrinsicPlayerEstimate,
)
from fsffl.analytics.dynasty_position_room import build_dynasty_position_rooms


def read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise AssertionError(f"empty output {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rules() -> LeagueRules:
    return LeagueRules(
        team_count=12, roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING,
    )


def terminal_regen(historical_panel: Path, source_board: Path, module, out: Path):
    # Exact current materializer's feature construction; no candidate fitting.
    raw = module.scored_raw_frame(pd.read_csv(historical_panel))
    board = pd.read_csv(source_board)
    connected_points = {
        (str(row.player_id), int(row.season)): float(row.fantasyPoints)
        for row in raw.itertuples()
    }
    terminal_rows = []
    for row in board.itertuples():
        historical_id = None if pd.isna(row.historical_gsis_id) else str(row.historical_gsis_id)
        prior = connected_points.get((historical_id, 2025)) if historical_id is not None else None
        terminal_rows.append({
            "player_id": str(row.player_id),
            "position": str(row.position),
            "age_years": float(row.age),
            "experience_years": float(row.experience),
            "current_points": max(0.0, float(row.league_y1_points)),
            "prior_points": prior,
            "prior_missing": prior is None,
            "current_points_coordinate": module.SCORING_COORDINATE,
            "prior_points_coordinate": module.SCORING_COORDINATE,
            "live_feature_transport_limitation": (
                "terminal calibration uses the exact FSFFL scoring transform "
                "of frozen historical standard production; 2026 uses the "
                "governed connected-league full-season Y1 expectation"
            ),
        })
    terminal = pd.DataFrame(terminal_rows).sort_values("player_id").reset_index(drop=True)
    if len(terminal) != 335 or terminal.player_id.nunique() != 335:
        raise AssertionError("regenerated terminal expected 335 unique subjects")
    terminal.to_csv(out, index=False)
    return terminal


def compare_terminal(reference: Path, regenerated: Path):
    a, b = read(reference), read(regenerated)
    keys = ("player_id", "position")
    x = {tuple(row[k] for k in keys): row for row in a}
    y = {tuple(row[k] for k in keys): row for row in b}
    assert len(a) == len(b) == len(x) == len(y) == 335
    assert x.keys() == y.keys()
    assert set(a[0]) == set(b[0])
    numerical = ("age_years", "experience_years", "current_points", "prior_points")
    report = {"rows": 335, "ref_sha256": digest(reference),
              "regenerated_sha256": digest(regenerated),
              "categorical_mismatches": [], "numeric_mismatches": [],
              "numeric_max_absolute_diff": {}, "numeric_exact_equal": True}
    for key in sorted(x):
        for column in a[0]:
            aa, bb = x[key][column], y[key][column]
            if column in numerical:
                if aa == bb:
                    continue
                if aa == "" and bb == "":
                    continue
                try:
                    av, bv = float(aa), float(bb)
                    delta = abs(av - bv)
                    report["numeric_max_absolute_diff"][column] = max(
                        report["numeric_max_absolute_diff"].get(column, 0.0), delta
                    )
                    if av != bv:
                        report["numeric_mismatches"].append(
                            {"key": key, "field": column, "expected": av, "got": bv, "delta": delta}
                        )
                        report["numeric_exact_equal"] = False
                except ValueError:
                    report["numeric_mismatches"].append(
                        {"key": key, "field": column, "expected": aa, "got": bb}
                    )
                    report["numeric_exact_equal"] = False
            elif aa != bb:
                report["categorical_mismatches"].append(
                    {"key": key, "field": column, "expected": aa, "got": bb}
                )
    report["categorical_difference_count"] = len(report["categorical_mismatches"])
    report["numeric_difference_count"] = len(report["numeric_mismatches"])
    return report


def forecast_contract(csv_path: Path) -> LongHorizonForecastAuthorityContract:
    raw = read(csv_path)
    rows = tuple(LongHorizonPolicyForecast.model_validate({**item, "year_index": int(item["year_index"])}) for item in raw)
    return LongHorizonForecastAuthorityContract(
        evaluation_season=2026,
        scoring_coordinate="connected_league_fantasy_points",
        forecast_model_version=rows[0].model_version,
        forecast_source=rows[0].source,
        forecasts=rows,
        provenance={"audit_only": True},
    )


def current_intrinsic(rows: list[dict]) -> ShapleyIntrinsicContract:
    # The accepted static 2026 Current Shapley audit is a fixed Y1-Y3
    # controlled input, NOT a claim to reproduce the latest live Current State.
    provenance = ShapleyHorizonProvenance(
        authority="frozen_335_current_shapley_diagnostic",
        source="materialize_shapley_comparison_audit",
        model_version="intrinsic-shapley-i1-v1",
    )
    uncertainty = ShapleyHorizonUncertainty(evidence_path="frozen_335_diagnostic")
    estimates = []
    for row in sorted(rows, key=lambda x: x["player_id"]):
        contributions = tuple(
            ShapleyIntrinsicHorizonContribution(
                year_index=year, target_season=2025 + year,
                raw_shapley_contribution=float(row[col]),
                discount_factor=1.0,
                discounted_contribution=float(row[col]),
                provenance=provenance, uncertainty=uncertainty,
            ) for year, col in ((1, "year1_shapley"), (2, "year2_expected_shapley"),
                                (3, "year3_expected_shapley"))
        )
        estimates.append(ShapleyIntrinsicPlayerEstimate(
            player_id=row["player_id"],
            raw_intrinsic_value=sum(t.raw_shapley_contribution for t in contributions),
            contributions=contributions,
            diagnostic_h1=DiagnosticH1Evidence(
                target_season=2026, anticipated_points=0.0,
                provenance=provenance.model_copy(update={"diagnostic_only": True, "included_in_intrinsic": False}),
                uncertainty=uncertainty, included_in_intrinsic=False,
            ),
        ))
    return ShapleyIntrinsicContract(
        status=ShapleyIntrinsicAvailability.READY,
        evaluation_season=2026, completed_source_season=2025,
        target_years=(2026, 2027, 2028),
        completed_source_provenance=CompletedSourceFactProvenance(source_version="frozen-335-current-diagnostic"),
        coverage=ShapleyIntrinsicCoverage(
            player_count=len(estimates), year_1_forecast_players=len(estimates),
            year_2_i1_players=len(estimates), year_3_i1_players=len(estimates),
            rich_path_players=len(estimates), reduced_or_fallback_players=0),
        estimates=tuple(estimates),
    )


def tails(path: Path, rr: LeagueRules):
    features = {}
    for row in read(path):
        prior = row["prior_points"]
        features[row["player_id"]] = CareerTailFeatures(
            player_id=row["player_id"], position=Position(row["position"]),
            age_years=float(row["age_years"]), experience_years=float(row["experience_years"]),
            current_points=float(row["current_points"]),
            prior_points=(float(prior) if prior and prior.lower() != "nan" else None),
            current_points_coordinate=row["current_points_coordinate"],
            prior_points_coordinate=row["prior_points_coordinate"],
            live_feature_transport_limitation=row["live_feature_transport_limitation"],
        )
    assert len(features) == 335
    return {
        pid: build_career_tail_authority(features[pid], rules=rr) for pid in sorted(features)
    }


def rank_map(values: dict[str, float]) -> dict[str, int]:
    ordered = sorted(values, key=lambda pid: (-values[pid], pid))
    rank = {}
    for index, pid in enumerate(ordered, 1):
        rank[pid] = index
    return rank


def synthetic_state(terminal_rows: list[dict], rr: LeagueRules) -> LeagueState:
    # 12 * 18 players, 3 QB / 6 RB / 6 WR / 3 TE per team.
    # 100% exact source IDs; never claim this is the user's actual league State.
    per_position = {"QB": 36, "RB": 72, "WR": 72, "TE": 36}
    teams = tuple(Team(team_id=f"synthetic-{n:02d}", league_id="career-405-semantic-fixture",
                       display_name=f"Synthetic {n:02d}") for n in range(12))
    assigned = {team.team_id: [] for team in teams}
    chosen = []
    for pos, count in per_position.items():
        candidates = sorted((row for row in terminal_rows if row["position"] == pos),
                            key=lambda r: (-float(r["current_points"]), r["player_id"]))[:count]
        assert len(candidates) == count
        for i, row in enumerate(candidates):
            assigned[teams[i % 12].team_id].append(row["player_id"])
            chosen.append(row)
    assert len(chosen) == 216 and len({r["player_id"] for r in chosen}) == 216
    now = datetime(2026, 10, 7, tzinfo=UTC)
    proof = Provenance(source="career-405-audit-fixture", retrieved_at=now,
                       effective_at=now, source_version="semantic-pr1-only")
    return LeagueState(
        league=League(league_id="career-405-semantic-fixture", name="PR1 semantic #370 fixture",
                      season=2026, rules=rr),
        as_of=now, teams=teams,
        team_states=tuple(TeamState(team_id=t.team_id, roster=tuple(
            RosterEntry(player_id=pid, slot=RosterSlot.BENCH)
            for pid in assigned[t.team_id])) for t in teams),
        players=tuple(Player(player_id=r["player_id"], full_name=r["player_id"],
                             position=Position(r["position"])) for r in chosen),
        player_states=tuple(PlayerState(player_id=r["player_id"], as_of=now, provenance=proof)
                            for r in chosen),
    )


def comparison(a: float, b: float):
    return {"ref": a, "replay": b, "delta": b - a}


def main():
    parser = argparse.ArgumentParser()
    for name in ("reference", "replay", "panel", "source_board", "out"):
        parser.add_argument("--" + name.replace("_", "-"), required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    accepted_term = args.reference / "FOUNDATION4_CURRENT_TERMINAL_FEATURES_335.csv"
    regen_term = args.out / "FOUNDATION4_CURRENT_TERMINAL_FEATURES_REGENERATED_335.csv"
    from scripts import materialize_foundation4_fsffl_coordinate as source
    terminal_frame = terminal_regen(args.panel, args.source_board, source, regen_term)
    term_report = compare_terminal(accepted_term, regen_term)
    (args.out / "terminal_parity.json").write_text(json.dumps(term_report, indent=2, sort_keys=True))
    print("TERMINAL", json.dumps({k: v for k, v in term_report.items()
                                  if k not in ("categorical_mismatches", "numeric_mismatches")}), flush=True)
    if term_report["categorical_difference_count"] or term_report["numeric_difference_count"]:
        # Do not route unmatched terminal features into the accepted economics.
        raise AssertionError("Terminal directly regenerated rows differ from accepted frozen terminal")

    rr = rules()
    # The current Y1-Y3 component is calculated ONCE from the existing
    # frozen current Shapley audit; identical in both Career builds.
    import scripts.materialize_shapley_comparison_audit as audit
    audit.OUT = args.out / "unchanged_current"
    audit.main()
    cur_rows = read(audit.OUT / "SHAPLEY_CURRENT_BOARD_335.csv")
    current = current_intrinsic(cur_rows)
    assert len(cur_rows) == len(current.estimates) == 335
    fixed_tail = tails(accepted_term, rr)
    print("BUILD_REFERENCE_LONGTERM 2048 governed permutations", flush=True)
    ref_forecast = forecast_contract(args.reference / "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_335.csv")
    ref_long = build_long_term_intrinsic_shadow(ref_forecast, rules=rr)
    print("BUILD_REPLAY_LONGTERM 2048 governed permutations", flush=True)
    replay_forecast = forecast_contract(args.replay / "FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_335.csv")
    replay_long = build_long_term_intrinsic_shadow(replay_forecast, rules=rr)
    print("BUILD_CAREER", flush=True)
    a = build_career_forward_intrinsic_shadow(current, ref_long, fixed_tail)
    b = build_career_forward_intrinsic_shadow(current, replay_long, fixed_tail)
    assert a.player_count == b.player_count == 335

    ar = {e.player_id: e for e in a.estimates}
    br = {e.player_id: e for e in b.estimates}
    al = {e.player_id: e for e in ref_long.estimates}
    bl = {e.player_id: e for e in replay_long.estimates}
    assert ar.keys() == br.keys() == al.keys() == bl.keys()
    rank_a = rank_map({k: x.raw_career_forward_reference for k, x in ar.items()})
    rank_b = rank_map({k: x.raw_career_forward_reference for k, x in br.items()})
    rank_la = rank_map({k: x.model_authority.reference_center for k, x in al.items()})
    rank_lb = rank_map({k: x.model_authority.reference_center for k, x in bl.items()})

    career_rows = []
    long_rows = []
    policy_rows = []
    for pid in sorted(ar):
        ca, cb, la, lb = ar[pid], br[pid], al[pid], bl[pid]
        career_rows.append({
            "player_id": pid, "position": ca.position.value,
            "current_y1_y3_ref": ca.current_intrinsic_raw_y1_y3,
            "current_y1_y3_replay": cb.current_intrinsic_raw_y1_y3,
            "terminal_y8plus_ref": ca.terminal_raw_y8_plus_reference,
            "terminal_y8plus_replay": cb.terminal_raw_y8_plus_reference,
            "long_y4_y7_ref": ca.long_horizon_raw_y4_y7_reference,
            "long_y4_y7_replay": cb.long_horizon_raw_y4_y7_reference,
            "long_y4_y7_delta": cb.long_horizon_raw_y4_y7_reference - ca.long_horizon_raw_y4_y7_reference,
            "career_raw_ref": ca.raw_career_forward_reference,
            "career_raw_replay": cb.raw_career_forward_reference,
            "career_raw_delta": cb.raw_career_forward_reference - ca.raw_career_forward_reference,
            "career_authority_low_ref": ca.model_authority.low,
            "career_authority_low_replay": cb.model_authority.low,
            "career_authority_low_delta": cb.model_authority.low - ca.model_authority.low,
            "career_authority_high_ref": ca.model_authority.high,
            "career_authority_high_replay": cb.model_authority.high,
            "career_authority_high_delta": cb.model_authority.high - ca.model_authority.high,
            "career_authority_width_delta": cb.model_authority.width - ca.model_authority.width,
            "career_rank_ref": rank_a[pid], "career_rank_replay": rank_b[pid],
            "career_rank_delta": rank_b[pid] - rank_a[pid],
            "long_rank_ref": rank_la[pid], "long_rank_replay": rank_lb[pid],
            "long_rank_delta": rank_lb[pid] - rank_la[pid],
            "long_value_index_ref": la.value_index_reference_0_10000,
            "long_value_index_replay": lb.value_index_reference_0_10000,
            "long_value_index_delta": lb.value_index_reference_0_10000 - la.value_index_reference_0_10000,
        })
        long_rows.append({
            "player_id": pid, "position": ca.position.value,
            "long_reference_ref": la.model_authority.reference_center,
            "long_reference_replay": lb.model_authority.reference_center,
            "long_reference_delta": lb.model_authority.reference_center - la.model_authority.reference_center,
            "long_low_delta": lb.model_authority.low - la.model_authority.low,
            "long_high_delta": lb.model_authority.high - la.model_authority.high,
            "long_rank_ref": rank_la[pid], "long_rank_replay": rank_lb[pid],
            "long_value_index_delta": lb.value_index_reference_0_10000 - la.value_index_reference_0_10000,
            **{f"y{n}_reference_delta": lb.annual[n-4].reference_center-la.annual[n-4].reference_center
               for n in (4,5,6,7)},
            **{f"y{n}_low_delta": lb.annual[n-4].authority_low-la.annual[n-4].authority_low
               for n in (4,5,6,7)},
            **{f"y{n}_high_delta": lb.annual[n-4].authority_high-la.annual[n-4].authority_high
               for n in (4,5,6,7)},
            **{f"y{n}_lo80_delta": lb.annual[n-4].combined_lo80-la.annual[n-4].combined_lo80
               for n in (4,5,6,7)},
            **{f"y{n}_hi80_delta": lb.annual[n-4].combined_hi80-la.annual[n-4].combined_hi80
               for n in (4,5,6,7)},
            **{f"y{n}_lo90_delta": lb.annual[n-4].combined_lo90-la.annual[n-4].combined_lo90
               for n in (4,5,6,7)},
            **{f"y{n}_hi90_delta": lb.annual[n-4].combined_hi90-la.annual[n-4].combined_hi90
               for n in (4,5,6,7)},
        })
        for t, u in zip(la.annual, lb.annual, strict=True):
            aa = {item.policy_id:item for item in t.policy_contributions}
            bb = {item.policy_id:item for item in u.policy_contributions}
            assert aa.keys() == bb.keys()
            for policy in sorted(aa):
                x,y = aa[policy],bb[policy]
                policy_rows.append({
                    "player_id":pid, "position":ca.position.value,
                    "year":t.year_index, "policy":policy,
                    **{f"{nm}_ref":getattr(x,nm) for nm in
                       ("central_shapley","lo80_shapley","hi80_shapley","lo90_shapley","hi90_shapley")},
                    **{f"{nm}_replay":getattr(y,nm) for nm in
                       ("central_shapley","lo80_shapley","hi80_shapley","lo90_shapley","hi90_shapley")},
                    **{f"{nm}_delta":getattr(y,nm)-getattr(x,nm) for nm in
                       ("central_shapley","lo80_shapley","hi80_shapley","lo90_shapley","hi90_shapley")},
                })
    write(args.out / "career_335_player_differences.csv", career_rows)
    write(args.out / "longterm_335_player_differences.csv", long_rows)
    write(args.out / "shapley_policy_contributions_differences.csv", policy_rows)

    state = synthetic_state(terminal_frame.to_dict(orient="records"), rr)
    ra = build_dynasty_position_rooms(state, career_forward=a, evidence_state_id=state.state_id)
    rb = build_dynasty_position_rooms(state, career_forward=b, evidence_state_id=state.state_id)
    assert len(ra) == len(rb) == 48
    rbmap = {(r.team_id,r.position):r for r in rb}
    rooms = []
    for x in ra:
        y = rbmap[(x.team_id,x.position)]
        assert x.evidence_complete and y.evidence_complete
        rooms.append({
            "team": x.team_id, "position": x.position.value,
            "roster_count_ref": x.rostered_player_count, "roster_count_replay": y.rostered_player_count,
            "room_raw_ref":x.room_raw, "room_raw_replay":y.room_raw,
            "room_raw_delta":y.room_raw-x.room_raw,
            "strength_index_ref":x.strength_index, "strength_index_replay":y.strength_index,
            "strength_index_delta":y.strength_index-x.strength_index,
            "league_rank_ref":x.league_rank, "league_rank_replay":y.league_rank,
            "league_rank_delta":y.league_rank-x.league_rank,
            "evidence_complete_ref": x.evidence_complete,
            "evidence_complete_replay": y.evidence_complete,
        })
    write(args.out / "dynasty_48_room_differences_SYNTHETIC.csv", rooms)

    numeric_cols = [
        "career_raw_delta","career_authority_low_delta","career_authority_high_delta",
        "career_authority_width_delta","long_y4_y7_delta",
        "long_value_index_delta"]
    stats = {
        name: {
            "max_abs": max(abs(float(r[name])) for r in career_rows),
            "mean_abs": sum(abs(float(r[name])) for r in career_rows)/len(career_rows),
            "nonzero_count": sum(float(r[name]) != 0.0 for r in career_rows),
        } for name in numeric_cols
    }
    policy_fields=("central_shapley","lo80_shapley","hi80_shapley","lo90_shapley","hi90_shapley")
    policy_stats={fld: {"max_abs": max(abs(float(r[fld+"_delta"])) for r in policy_rows),
                        "nonzero_count": sum(float(r[fld+"_delta"])!=0.0 for r in policy_rows)}
                  for fld in policy_fields}
    summary={
        "run_kind":"PR1 read-only semantic counterfactual, no model refit/reroute, no production State mutation",
        "reference_board_sha256":digest(args.reference/"FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_335.csv"),
        "replay_board_sha256":digest(args.replay/"FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_335.csv"),
        "terminal":term_report,
        "cohort":335,"shapley_permutations":ref_long.permutations,
        "shapley_horizon_seeds":list(ref_long.horizon_seeds),
        "same_current_335":set(x.player_id for x in current.estimates)==set(ar),
        "same_terminal_335":set(fixed_tail)==set(ar),
        "current_y1_y3_nonzero_diffs":sum(r["current_y1_y3_ref"]!=r["current_y1_y3_replay"] for r in career_rows),
        "terminal_y8plus_nonzero_diffs":sum(r["terminal_y8plus_ref"]!=r["terminal_y8plus_replay"] for r in career_rows),
        "longterm_reference_ranks_changed":sum(r["long_rank_delta"] != 0 for r in career_rows),
        "longterm_index_changed":sum(r["long_value_index_delta"] != 0 for r in career_rows),
        "career_ranks_changed":sum(r["career_rank_delta"]!=0 for r in career_rows),
        "career_rank_max_abs_change":max(abs(r["career_rank_delta"]) for r in career_rows),
        "career_y4_y7_fields":stats,
        "shapley_policy_fields":policy_stats,
        "shapley_policy_rows":len(policy_rows),
        "dynasty_state":"synthetic complete-335-subset State 12 teams x 18, NOT historical/live State",
        "dynasty_rooms":len(rooms),
        "dynasty_ranks_changed":sum(r["league_rank_delta"]!=0 for r in rooms),
        "dynasty_strength_index_max_abs":max(abs(r["strength_index_delta"]) for r in rooms),
        "dynasty_room_raw_max_abs":max(abs(r["room_raw_delta"]) for r in rooms),
        "min_career_adjacent_rank_gap_ref":min(abs(career_rows[i]["career_raw_ref"]-career_rows[j]["career_raw_ref"])
                                              for i,j in zip(
                sorted(range(len(career_rows)), key=lambda k:-career_rows[k]["career_raw_ref"])[:-1],
                sorted(range(len(career_rows)), key=lambda k:-career_rows[k]["career_raw_ref"])[1:])),
        "meaning_of_live_rank":"Cannot assert live #370 rank parity without exact complete live State: #405 missing players remain",
    }
    (args.out/"semantic_parity_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
    print("FINAL_SUMMARY",json.dumps({k:v for k,v in summary.items()
         if k not in ("terminal","career_y4_y7_fields","shapley_policy_fields")},sort_keys=True),flush=True)


if __name__=="__main__":
    main()
