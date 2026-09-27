from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_injury_availability_time_to_return as base

OUT = Path("artifacts/research/current_football_state_h3_20260926")
HOLDOUTS = base.HOLDOUTS
RANDOM_STATE = base.RANDOM_STATE

RETURN_CAT = ("position", "severity", "injury_family")
RETURN_NUM = ("event_week", "weeks_remaining", "latent_availability", "delay")


def return_preprocessor():
    return ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), list(RETURN_CAT)),
            ("num", Pipeline([("scale", StandardScaler())]), list(RETURN_NUM)),
        ],
        remainder="drop",
    )


def fit_return_head(hazard_train: pd.DataFrame):
    model = Pipeline(
        [
            ("prep", return_preprocessor()),
            (
                "model",
                HistGradientBoostingClassifier(
                    learning_rate=0.06,
                    max_iter=160,
                    max_leaf_nodes=15,
                    l2_regularization=3.0,
                    min_samples_leaf=30,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )
    cols = list(RETURN_CAT) + list(RETURN_NUM)
    model.fit(hazard_train[cols], hazard_train["hazard_event"])
    return model


def fit_stage_a(train: pd.DataFrame):
    return base.fit_availability_models(train)["histgb"]


def stage_a_predict(model, rows: pd.DataFrame) -> np.ndarray:
    return np.clip(model.predict(rows[list(base.CAT) + list(base.NUM)]), 0.0, 1.0)


def chronology_preserving_inner_latents(x: pd.DataFrame, outer_origin: int) -> pd.DataFrame:
    parts = []
    for inner_origin in range(2016, outer_origin):
        tr = x[x.season < inner_origin].copy()
        ev = x[x.season == inner_origin].copy()
        if len(tr) < 1000 or ev.empty:
            continue
        model = fit_stage_a(tr)
        p = stage_a_predict(model, ev)
        parts.append(
            pd.DataFrame(
                {
                    "episode_id": ev.episode_id.to_numpy(int),
                    "inner_origin": int(inner_origin),
                    "latent_availability": p,
                }
            )
        )
    if not parts:
        return pd.DataFrame(columns=["episode_id", "inner_origin", "latent_availability"])
    return pd.concat(parts, ignore_index=True)


def build_joint_return_train(x: pd.DataFrame, outer_origin: int) -> tuple[pd.DataFrame, dict]:
    lat = chronology_preserving_inner_latents(x, outer_origin)
    eligible = x[x.episode_id.isin(lat.episode_id)].copy()
    h = base.build_hazard_rows(eligible)
    h = h.merge(lat[["episode_id", "latent_availability"]], on="episode_id", how="inner")
    meta = {
        "outer_origin": int(outer_origin),
        "inner_episode_n": int(lat.episode_id.nunique()),
        "inner_hazard_row_n": int(len(h)),
        "inner_origins": sorted(int(v) for v in lat.inner_origin.unique()) if len(lat) else [],
    }
    if len(h) < 1000 or h.hazard_event.nunique() < 2:
        raise RuntimeError(f"insufficient nested return-head support at outer origin {outer_origin}: {meta}")
    return h, meta


def predict_joint_return(eval_ep: pd.DataFrame, latent: np.ndarray, model) -> pd.DataFrame:
    latent_map = {int(eid): float(p) for eid, p in zip(eval_ep.episode_id, latent)}
    risk = []
    for r in eval_ep.itertuples():
        if bool(r.structurally_inconsistent_return):
            continue
        for delay in range(0, int(r.weeks_remaining) + 1):
            risk.append(
                {
                    "episode_id": int(r.episode_id),
                    "position": r.position,
                    "severity": r.severity,
                    "injury_family": r.injury_family,
                    "event_week": float(r.event_week),
                    "weeks_remaining": float(r.weeks_remaining),
                    "latent_availability": latent_map[int(r.episode_id)],
                    "delay": int(delay),
                }
            )
    rr = pd.DataFrame(risk)
    if rr.empty:
        return pd.DataFrame()
    cols = list(RETURN_CAT) + list(RETURN_NUM)
    rr["joint_hazard"] = np.clip(model.predict_proba(rr[cols])[:, 1], 1e-5, 1 - 1e-5)

    lookup = eval_ep.set_index("episode_id")
    out = []
    for eid, g in rr.groupby("episode_id"):
        g = g.sort_values("delay")
        e = lookup.loc[eid]
        surv = 1.0
        cdfs = {}
        for row in g.itertuples():
            surv *= 1.0 - float(row.joint_hazard)
            cdfs[int(row.delay)] = 1.0 - surv
        rec = {
            "episode_id": int(eid),
            "season": int(e.season),
            "position": e.position,
            "severity": e.severity,
            "injury_family": e.injury_family,
            "weeks_remaining": int(e.weeks_remaining),
            "games_to_return": float(e.games_to_return)
            if pd.notna(e.games_to_return) and not e.structurally_inconsistent_return
            else np.nan,
        }
        for kk in base.ENDPOINTS:
            rec[f"joint_p_return_by_{kk}"] = (
                cdfs.get(kk, cdfs[max(cdfs)]) if int(e.weeks_remaining) >= kk else np.nan
            )
        rec["joint_p_return_any"] = cdfs[max(cdfs)]
        ib = []
        for d, p in cdfs.items():
            y = int(
                pd.notna(e.games_to_return)
                and not e.structurally_inconsistent_return
                and float(e.games_to_return) <= d
            )
            ib.append((p - y) ** 2)
        rec["joint_ibs"] = float(np.mean(ib)) if ib else np.nan
        out.append(rec)
    return pd.DataFrame(out)


def run_joint(x: pd.DataFrame):
    all_avail = []
    all_return = []
    fold_rows = []
    nested_meta = []

    for T in range(2016, 2025):
        tr = x[x.season < T].copy()
        ev = x[x.season == T].copy()
        if len(tr) < 1000 or ev.empty:
            continue

        stage_a = fit_stage_a(tr)
        latent = stage_a_predict(stage_a, ev)
        av = ev[
            ["episode_id", "season", "position", "severity", "injury_family", "availability_target"]
        ].copy()
        av["joint_pred"] = latent
        av["origin"] = int(T)
        all_avail.append(av)

        if T in HOLDOUTS:
            htrain, meta = build_joint_return_train(x[x.season < T].copy(), T)
            nested_meta.append(meta)
            rmodel = fit_return_head(htrain)
            ttr = predict_joint_return(ev, latent, rmodel)
            ttr["origin"] = int(T)
            all_return.append(ttr)

    return (
        pd.concat(all_return, ignore_index=True),
        pd.concat(all_avail, ignore_index=True),
        nested_meta,
    )


def merge_prior_ttr(joint: pd.DataFrame, prior: pd.DataFrame) -> pd.DataFrame:
    cols = ["episode_id", "season"]
    need = []
    for name in ("severity", "histgb"):
        for kk in base.ENDPOINTS:
            need.append(f"{name}_p_return_by_{kk}")
        need += [f"{name}_p_return_any", f"{name}_ibs"]
    q = prior[cols + need].copy()
    out = joint.merge(q, on=cols, how="left", validate="one_to_one")
    if out[need].isna().all(axis=None):
        raise RuntimeError("prior return benchmark failed to merge")
    return out


def merge_prior_avail(joint: pd.DataFrame, prior: pd.DataFrame) -> pd.DataFrame:
    q = prior[["episode_id", "season", "severity_pred", "histgb_pred"]].copy()
    out = joint.merge(q, on=["episode_id", "season"], how="left", validate="one_to_one")
    if out[["severity_pred", "histgb_pred"]].isna().any(axis=None):
        raise RuntimeError("prior availability benchmark failed to merge")
    return out


def return_metrics_table(q: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, col in (
        ("severity", "severity"),
        ("separate_histgb", "histgb"),
        ("joint", "joint"),
    ):
        rows.append({"model": label, **base.endpoint_metrics(q, col)})
    return pd.DataFrame(rows)


def avail_metrics_table(q: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, col in (
        ("severity", "severity_pred"),
        ("separate_histgb", "histgb_pred"),
        ("joint", "joint_pred"),
    ):
        rows.append({"model": label, **base.avail_metrics(q, col)})
    return pd.DataFrame(rows)


def fold_metrics(ttr: pd.DataFrame, av: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for T in HOLDOUTS:
        rt = ttr[ttr.season == T]
        aa = av[av.season == T]
        for label, col in (("severity", "severity"), ("separate_histgb", "histgb"), ("joint", "joint")):
            rows.append(
                {
                    "component": "return_timing",
                    "season": T,
                    "model": label,
                    **base.endpoint_metrics(rt, col),
                }
            )
        for label, col in (
            ("severity", "severity_pred"),
            ("separate_histgb", "histgb_pred"),
            ("joint", "joint_pred"),
        ):
            rows.append(
                {
                    "component": "remaining_availability",
                    "season": T,
                    "model": label,
                    **base.avail_metrics(aa, col),
                }
            )
    return pd.DataFrame(rows)


def position_safety(ttr: pd.DataFrame, av: pd.DataFrame):
    ret = []
    for pos, g in ttr.groupby("position"):
        if len(g) < 100:
            continue
        jm = base.endpoint_metrics(g, "joint")
        sm = base.endpoint_metrics(g, "severity")
        hm = base.endpoint_metrics(g, "histgb")
        ret.append(
            {
                "position": pos,
                "n": len(g),
                "joint_mean_brier": jm["mean_brier"],
                "vs_severity_rel": jm["mean_brier"] / sm["mean_brier"] - 1,
                "vs_separate_histgb_rel": jm["mean_brier"] / hm["mean_brier"] - 1,
            }
        )

    ava = []
    for pos, g in av.groupby("position"):
        if len(g) < 100:
            continue
        jm = base.avail_metrics(g, "joint_pred")
        sm = base.avail_metrics(g, "severity_pred")
        hm = base.avail_metrics(g, "histgb_pred")
        ava.append(
            {
                "position": pos,
                "n": len(g),
                "joint_mae": jm["mae"],
                "vs_severity_rel": jm["mae"] / sm["mae"] - 1,
                "vs_separate_histgb_rel": jm["mae"] / hm["mae"] - 1,
            }
        )
    return pd.DataFrame(ret), pd.DataFrame(ava)


def evaluate_gates(
    ttr: pd.DataFrame,
    av: pd.DataFrame,
    folds: pd.DataFrame,
    ret_pooled: pd.DataFrame,
    av_pooled: pd.DataFrame,
    ret_pos: pd.DataFrame,
    av_pos: pd.DataFrame,
):
    rp = ret_pooled.set_index("model")
    ap = av_pooled.set_index("model")

    rsev, rsep, rj = rp.loc["severity"], rp.loc["separate_histgb"], rp.loc["joint"]
    asev, asep, aj = ap.loc["severity"], ap.loc["separate_histgb"], ap.loc["joint"]

    r_sev_wins = 0
    r_sep_nonworse = 0
    a_sev_wins = 0
    a_sep_bad = 0
    for T in HOLDOUTS:
        rf = folds[(folds.component == "return_timing") & (folds.season == T)].set_index("model")
        af = folds[(folds.component == "remaining_availability") & (folds.season == T)].set_index("model")
        r_sev_wins += int(rf.loc["joint", "mean_brier"] < rf.loc["severity", "mean_brier"])
        r_sep_nonworse += int(rf.loc["joint", "mean_brier"] <= rf.loc["separate_histgb", "mean_brier"])
        a_sev_wins += int(af.loc["joint", "mae"] < af.loc["severity", "mae"])
        a_sep_bad += int(af.loc["joint", "mae"] > 1.03 * af.loc["separate_histgb", "mae"])

    availability_original = bool(
        aj.mae <= 0.98 * asev.mae
        and aj.rmse <= 1.03 * asev.rmse
        and abs(aj.bias) <= abs(asev.bias) + 0.02
        and a_sev_wins >= 4
        and (av_pos.vs_severity_rel <= 0.07).all()
    )
    availability_noninferior = bool(
        aj.mae <= 1.01 * asep.mae
        and aj.rmse <= 1.01 * asep.rmse
        and abs(aj.bias) <= abs(asep.bias) + 0.01
        and (av_pos.vs_separate_histgb_rel <= 0.03).all()
        and a_sep_bad <= 2
    )

    return_original = bool(
        rj.mean_brier <= 0.98 * rsev.mean_brier
        and rj.integrated_brier <= 0.99 * rsev.integrated_brier
        and rj.mean_log_loss <= 1.03 * rsev.mean_log_loss
        and rj.mean_abs_calibration_error <= rsev.mean_abs_calibration_error + 0.02
        and r_sev_wins >= 4
        and (ret_pos.vs_severity_rel <= 0.07).all()
    )
    return_direct = bool(
        rj.mean_brier < rsep.mean_brier
        and rj.integrated_brier <= 1.01 * rsep.integrated_brier
        and (ret_pos.vs_separate_histgb_rel <= 0.03).all()
        and r_sep_nonworse >= 3
    )

    minimum_support = bool(
        len(av) >= 1500
        and len(ttr) >= 1500
        and set(int(v) for v in av.season.unique()) == set(HOLDOUTS)
        and set(int(v) for v in ttr.season.unique()) == set(HOLDOUTS)
    )

    return {
        "minimum_support": minimum_support,
        "availability_original_gate": availability_original,
        "availability_noninferiority_to_separate_histgb": availability_noninferior,
        "return_original_gate": return_original,
        "return_direct_improvement_over_separate_histgb": return_direct,
        "joint_clears_all_frozen_gates": bool(
            minimum_support
            and availability_original
            and availability_noninferior
            and return_original
            and return_direct
        ),
        "holdout_counts": {
            "return_brier_wins_vs_severity": int(r_sev_wins),
            "return_brier_nonworse_vs_separate_histgb": int(r_sep_nonworse),
            "availability_mae_wins_vs_severity": int(a_sev_wins),
            "availability_holdouts_gt3pct_worse_than_separate_histgb": int(a_sep_bad),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=Path, required=True)
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--prior-dir", type=Path, required=True)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    episodes = pd.read_csv(args.episodes)
    career = pd.read_csv(args.career_panel)
    x = base.prepare(episodes, career)

    joint_ttr, joint_av_all, nested_meta = run_joint(x)
    prior_ttr = pd.read_csv(args.prior_dir / "INJURY_RETURN_TIMING_OOT_PREDICTIONS.csv")
    prior_av = pd.read_csv(args.prior_dir / "INJURY_AVAILABILITY_OOT_PREDICTIONS.csv")

    joint_av_hold = joint_av_all[joint_av_all.season.isin(HOLDOUTS)].copy()
    ttr = merge_prior_ttr(joint_ttr, prior_ttr)
    av = merge_prior_avail(joint_av_hold, prior_av)

    ret_pooled = return_metrics_table(ttr)
    av_pooled = avail_metrics_table(av)
    folds = fold_metrics(ttr, av)
    ret_pos, av_pos = position_safety(ttr, av)

    conf_input = joint_av_all.copy()
    conf_summary, conf_rows = base.conformal_availability(conf_input, "joint")

    gates = evaluate_gates(ttr, av, folds, ret_pooled, av_pooled, ret_pos, av_pos)

    benchmark_delta = {
        "max_abs_joint_vs_separate_histgb_availability_prediction_delta": float(
            np.max(np.abs(av.joint_pred.to_numpy(float) - av.histgb_pred.to_numpy(float)))
        ),
        "pooled_return_mean_brier_relative_to_separate_histgb": float(
            ret_pooled.set_index("model").loc["joint", "mean_brier"]
            / ret_pooled.set_index("model").loc["separate_histgb", "mean_brier"]
            - 1
        ),
        "pooled_availability_mae_relative_to_separate_histgb": float(
            av_pooled.set_index("model").loc["joint", "mae"]
            / av_pooled.set_index("model").loc["separate_histgb", "mae"]
            - 1
        ),
    }

    result = {
        "study": "joint-injury-availability-followup",
        "authority": "research_only_no_production_change",
        "validation_label": "follow_up_comparative_validation_not_pristine_final_holdout",
        "episode_n": int(len(x)),
        "holdouts": list(HOLDOUTS),
        "architecture": "availability_latent_hazard",
        "nested_return_training": nested_meta,
        "return_timing_pooled": ret_pooled.to_dict("records"),
        "remaining_availability_pooled": av_pooled.to_dict("records"),
        "return_position_safety": ret_pos.to_dict("records"),
        "availability_position_safety": av_pos.to_dict("records"),
        "conformal": conf_summary.to_dict("records"),
        "benchmark_reproduction": benchmark_delta,
        "gates": gates,
        "disposition": (
            "joint_architecture_research_challenger_supported"
            if gates["joint_clears_all_frozen_gates"]
            else "retain_separate_availability_and_leave_time_to_return_unpromoted"
        ),
        "guards": {
            "conditional_healthy_production_changed": False,
            "post_return_role_changed": False,
            "recurrence_or_h2_h3_changed": False,
            "production_h3_changed": False,
            "intrinsic_changed": False,
            "provider_ros_authority_changed": False,
        },
    }

    folds.to_csv(OUT / "JOINT_INJURY_AVAILABILITY_FOLD_METRICS.csv", index=False)
    ret_pooled.to_csv(OUT / "JOINT_INJURY_RETURN_POOLED_METRICS.csv", index=False)
    av_pooled.to_csv(OUT / "JOINT_INJURY_AVAILABILITY_POOLED_METRICS.csv", index=False)
    ret_pos.to_csv(OUT / "JOINT_INJURY_RETURN_POSITION_SAFETY.csv", index=False)
    av_pos.to_csv(OUT / "JOINT_INJURY_AVAILABILITY_POSITION_SAFETY.csv", index=False)
    conf_summary.to_csv(OUT / "JOINT_INJURY_AVAILABILITY_CONFORMAL_SUMMARY.csv", index=False)
    conf_rows.to_csv(OUT / "JOINT_INJURY_AVAILABILITY_CONFORMAL_PREDICTIONS.csv", index=False)
    ttr.to_csv(OUT / "JOINT_INJURY_RETURN_OOT_PREDICTIONS.csv", index=False)
    av.to_csv(OUT / "JOINT_INJURY_AVAILABILITY_OOT_PREDICTIONS.csv", index=False)
    (OUT / "JOINT_INJURY_AVAILABILITY_RESULT.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
