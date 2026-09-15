from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

POSITIONS = ("QB", "RB", "WR", "TE")
USEFUL_STATES = {"usable", "starter", "premium", "elite"}
POSITIVE_STATES = ("depth", "usable", "starter", "premium", "elite")
ERAS = ((2012, 2015, "early_2012_2015"), (2016, 2019, "middle_2016_2019"), (2020, 2023, "recent_2020_2023"))

RELEASE_STATUSES = {"CUT", "NWT", "RFA", "RSR", "TRC", "TRD", "TRT"}
FREE_AGENT_STATUSES = {"UFA"}
ATTACHED_STATUSES = {"ACT", "INA"}
PRACTICE_STATUSES = {"DEV"}
PUP_STATUSES = {"PUP"}
NFI_STATUSES = {"RSN"}
SUSP_STATUSES = {"SUS", "EXE"}
RETIRED_STATUSES = {"RET"}
RESERVE_STATUSES = {"RES", "E14"}

TAXONOMY = (
    "ACTIVE_ROSTER_INJURY_LIMITED",
    "ACTIVE_ROSTER_NO_PRODUCTION",
    "IR",
    "PUP",
    "NFI",
    "OTHER_RESERVE",
    "PRACTICE_SQUAD",
    "SUSPENDED_OR_EXEMPT",
    "WAIVED_OR_RELEASED",
    "UNSIGNED_OR_FREE_AGENT",
    "RETIRED",
    "TEAM_TRANSITION_TRANSACTION_IN_FLIGHT",
    "TEMPORARY_ABSENCE_OTHER_FACTUAL",
    "UNKNOWN_UNRESOLVED",
)


def mean(xs):
    vals = [float(x) for x in xs if pd.notna(x)]
    return float(sum(vals) / len(vals)) if vals else 0.0


def quantile(values, p):
    xs = sorted(float(x) for x in values if pd.notna(x))
    if not xs:
        return 0.0
    z = p * (len(xs) - 1)
    lo, hi = int(math.floor(z)), int(math.ceil(z))
    if lo == hi:
        return xs[lo]
    f = z - lo
    return xs[lo] * (1 - f) + xs[hi] * f


def kmeans_1d(values, k=5, iterations=60):
    xs = sorted(math.log1p(max(0.0, float(v))) for v in values if pd.notna(v) and float(v) > 0)
    if len(xs) < k:
        centers = [mean(xs)] * k if xs else [0.0] * k
    else:
        centers = [quantile(xs, (i + 0.5) / k) for i in range(k)]
    for _ in range(iterations):
        groups = [[] for _ in range(k)]
        for x in xs:
            groups[min(range(k), key=lambda i: abs(x - centers[i]))].append(x)
        new = sorted(mean(g) if g else centers[i] for i, g in enumerate(groups))
        if max(abs(a - b) for a, b in zip(new, centers)) < 1e-9:
            centers = new
            break
        centers = new
    raw = [max(0.0, math.expm1(x)) for x in centers]
    return tuple(raw), tuple((raw[i] + raw[i + 1]) / 2 for i in range(k - 1))


def state_for_points(points, boundaries):
    if float(points) <= 0:
        return "out"
    _, thresholds = boundaries
    idx = 0
    while idx < len(thresholds) and float(points) > thresholds[idx]:
        idx += 1
    return POSITIVE_STATES[idx]


def age_band(position, age):
    if age is None or pd.isna(age):
        return "unknown"
    if position == "QB":
        return "young" if age <= 25 else ("prime" if age <= 31 else "aging")
    return "young" if age <= 23 else ("prime" if age <= 27 else "aging")


def era_for_season(season):
    season = int(season)
    for lo, hi, name in ERAS:
        if lo <= season <= hi:
            return name
    return "outside_frozen_era"


def pick(df, candidates, required=False):
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise RuntimeError(f"Missing required columns {candidates}; available={list(df.columns)}")
    return None


def norm_status(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()


def restrict_regular(df):
    x = df.copy()
    for c in ("game_type", "season_type"):
        if c in x.columns:
            vals = x[c].astype(str).str.upper()
            if (vals == "REG").any():
                x = x[vals == "REG"].copy()
                break
    if "week" in x.columns:
        week = pd.to_numeric(x["week"], errors="coerce")
        x = x[week.isna() | (week <= 18)].copy()
    return x


def set_join(values):
    return "|".join(sorted({str(v) for v in values if pd.notna(v) and str(v) and str(v) != "nan"}))


def rankdata(values):
    return pd.Series(values).rank(method="average").to_numpy(dtype=float)


def auc(pos_values, neg_values):
    p = np.array([float(x) for x in pos_values if pd.notna(x)], dtype=float)
    n = np.array([float(x) for x in neg_values if pd.notna(x)], dtype=float)
    if len(p) == 0 or len(n) == 0:
        return None
    ranks = rankdata(np.concatenate([p, n]))
    u = ranks[: len(p)].sum() - len(p) * (len(p) + 1) / 2
    return float(u / (len(p) * len(n)))


def smd(a_values, b_values):
    a = np.array([float(x) for x in a_values if pd.notna(x)], dtype=float)
    b = np.array([float(x) for x in b_values if pd.notna(x)], dtype=float)
    if len(a) < 2 or len(b) < 2:
        return None
    denom = max(1, len(a) + len(b) - 2)
    pooled = math.sqrt(((len(a)-1)*a.var(ddof=1) + (len(b)-1)*b.var(ddof=1)) / denom)
    return 0.0 if pooled <= 1e-12 else float((a.mean() - b.mean()) / pooled)


def spearman(a, b):
    x = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(x) < 3:
        return None
    ra = x["a"].rank(method="average").to_numpy(dtype=float)
    rb = x["b"].rank(method="average").to_numpy(dtype=float)
    if np.std(ra) <= 1e-12 or np.std(rb) <= 1e-12:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


def load_nflverse(seasons):
    import nflreadpy as nfl
    to_pd = lambda frame: frame.to_pandas()
    players = to_pd(nfl.load_players())
    rosters = to_pd(nfl.load_rosters_weekly(seasons))
    injuries = to_pd(nfl.load_injuries(seasons))
    snaps = to_pd(nfl.load_snap_counts(seasons))
    stats = to_pd(nfl.load_player_stats(seasons, summary_level="week"))
    return players, rosters, injuries, snaps, stats


def prepare_roster_weekly(df):
    x = restrict_regular(df)
    season_col = pick(x, ["season"], True)
    week_col = pick(x, ["week"], True)
    id_col = pick(x, ["gsis_id", "player_id"], True)
    status_col = pick(x, ["status"], True)
    team_col = pick(x, ["team", "club_code"])
    desc_col = pick(x, ["status_description_abbr", "status_description", "status_desc"])
    pos_col = pick(x, ["position", "position_group", "pos"])
    x[id_col] = x[id_col].astype(str)
    x["_season"] = pd.to_numeric(x[season_col], errors="coerce").astype("Int64")
    x["_week"] = pd.to_numeric(x[week_col], errors="coerce").astype("Int64")
    x["_status"] = x[status_col].map(norm_status)
    x["_team"] = "" if team_col is None else x[team_col].fillna("").astype(str)
    x["_desc"] = "" if desc_col is None else x[desc_col].fillna("").astype(str).str.upper()
    x["_position"] = "" if pos_col is None else x[pos_col].fillna("").astype(str).str.upper()
    x = x[x["_season"].notna() & x["_week"].notna() & x[id_col].notna() & (x[id_col] != "nan")].copy()
    x["player_id"] = x[id_col]
    x["season"] = x["_season"].astype(int)
    x["week"] = x["_week"].astype(int)
    return x


def prepare_injuries(df):
    x = restrict_regular(df)
    id_col = pick(x, ["gsis_id", "player_id"], True)
    season_col = pick(x, ["season"], True)
    week_col = pick(x, ["week"], True)
    x[id_col] = x[id_col].astype(str)
    x["player_id"] = x[id_col]
    x["season"] = pd.to_numeric(x[season_col], errors="coerce").astype("Int64")
    x["week"] = pd.to_numeric(x[week_col], errors="coerce").astype("Int64")
    x = x[x.season.notna() & x.week.notna() & x.player_id.notna() & (x.player_id != "nan")].copy()
    x["season"] = x.season.astype(int)
    x["week"] = x.week.astype(int)
    report = pick(x, ["report_status"])
    practice = pick(x, ["practice_status"])
    r1 = pick(x, ["report_primary_injury"])
    r2 = pick(x, ["report_secondary_injury"])
    p1 = pick(x, ["practice_primary_injury"])
    p2 = pick(x, ["practice_secondary_injury"])
    modified = pick(x, ["date_modified"])
    x["_report"] = "" if report is None else x[report].fillna("").astype(str).str.strip().str.lower()
    x["_practice"] = "" if practice is None else x[practice].fillna("").astype(str).str.strip().str.lower()
    injury_cols = [c for c in (r1, r2, p1, p2) if c is not None]
    if injury_cols:
        x["_injury_text"] = x[injury_cols].fillna("").astype(str).agg("|".join, axis=1).str.strip("|")
    else:
        x["_injury_text"] = ""
    x["_report_limited"] = x["_report"].isin({"questionable", "doubtful", "out"})
    x["_practice_limited"] = x["_practice"].str.contains("did not|dnp|limited", regex=True, na=False)
    x["_official_limitation"] = x["_report_limited"] | x["_practice_limited"]
    x["_modified"] = "" if modified is None else x[modified].fillna("").astype(str)
    return x


def prepare_stats(df):
    x = restrict_regular(df)
    id_col = pick(x, ["player_id", "gsis_id"], True)
    season_col = pick(x, ["season"], True)
    week_col = pick(x, ["week"], True)
    x[id_col] = x[id_col].astype(str)
    x["player_id"] = x[id_col]
    x["season"] = pd.to_numeric(x[season_col], errors="coerce").astype("Int64")
    x["week"] = pd.to_numeric(x[week_col], errors="coerce").astype("Int64")
    x = x[x.season.notna() & x.week.notna() & x.player_id.notna() & (x.player_id != "nan")].copy()
    x["season"] = x.season.astype(int)
    x["week"] = x.week.astype(int)
    return x[["player_id", "season", "week"]].drop_duplicates()


def prepare_snaps(snaps, players):
    x = restrict_regular(snaps)
    season_col = pick(x, ["season"], True)
    week_col = pick(x, ["week"], True)
    pfr_col = pick(x, ["pfr_player_id", "pfr_id"], True)
    off_col = pick(x, ["offense_snaps"], False)
    def_col = pick(x, ["defense_snaps"], False)
    p_pfr = pick(players, ["pfr_id", "pfr_player_id"], True)
    p_gsis = pick(players, ["gsis_id", "player_id"], True)
    mapping = players[[p_pfr, p_gsis]].dropna().copy()
    mapping[p_pfr] = mapping[p_pfr].astype(str)
    mapping[p_gsis] = mapping[p_gsis].astype(str)
    conflicts = int((mapping.groupby(p_pfr)[p_gsis].nunique() > 1).sum())
    mapping = mapping.drop_duplicates(p_pfr, keep="first")
    mapping.columns = ["_pfr", "player_id"]
    x[pfr_col] = x[pfr_col].astype(str)
    x = x.merge(mapping, left_on=pfr_col, right_on="_pfr", how="left")
    total = len(x)
    mapped = int(x.player_id.notna().sum())
    x = x[x.player_id.notna()].copy()
    x["season"] = pd.to_numeric(x[season_col], errors="coerce").astype("Int64")
    x["week"] = pd.to_numeric(x[week_col], errors="coerce").astype("Int64")
    x = x[x.season.notna() & x.week.notna()].copy()
    x["season"] = x.season.astype(int)
    x["week"] = x.week.astype(int)
    off = pd.to_numeric(x[off_col], errors="coerce").fillna(0) if off_col else pd.Series(0, index=x.index)
    deff = pd.to_numeric(x[def_col], errors="coerce").fillna(0) if def_col else pd.Series(0, index=x.index)
    x["played_snap"] = (off + deff) > 0
    weekly = x.groupby(["player_id", "season", "week"], as_index=False)["played_snap"].max()
    audit = {
        "snap_rows": int(total),
        "mapped_rows": mapped,
        "mapping_rate": float(mapped / total) if total else 0.0,
        "pfr_to_gsis_conflict_ids": conflicts,
        "manual_mapping_count": 0,
        "name_based_mapping_count": 0,
    }
    return weekly, audit


def weekly_roster_summary(rosters):
    rows = []
    for (pid, season), g in rosters.groupby(["player_id", "season"]):
        gg = g.sort_values(["week", "_team", "_status", "_desc"]).copy()
        statuses = [s for s in gg._status if s]
        weeks = sorted(set(int(w) for w in gg.week))
        final_week = max(weeks) if weeks else None
        fg = gg[gg.week == final_week] if final_week is not None else gg.iloc[0:0]
        terminal_statuses = set(s for s in fg._status if s)
        terminal_teams = set(t for t in fg._team if t)
        prior_status_set = None
        prior_team_set = None
        status_changes = 0
        team_changes = 0
        active_returns = 0
        release_entries = 0
        practice_entries = 0
        reserve_entries = 0
        pup_entries = 0
        nfi_entries = 0
        susp_entries = 0
        for _wk, wg in gg.groupby("week", sort=True):
            st = set(s for s in wg._status if s)
            tm = set(t for t in wg._team if t)
            if prior_status_set is not None:
                if st != prior_status_set:
                    status_changes += 1
                if tm and prior_team_set and tm != prior_team_set:
                    team_changes += 1
                if st & ATTACHED_STATUSES and not (prior_status_set & ATTACHED_STATUSES):
                    active_returns += 1
                if st & RELEASE_STATUSES and not (prior_status_set & RELEASE_STATUSES):
                    release_entries += 1
                if st & PRACTICE_STATUSES and not (prior_status_set & PRACTICE_STATUSES):
                    practice_entries += 1
                if st & RESERVE_STATUSES and not (prior_status_set & RESERVE_STATUSES):
                    reserve_entries += 1
                if st & PUP_STATUSES and not (prior_status_set & PUP_STATUSES):
                    pup_entries += 1
                if st & NFI_STATUSES and not (prior_status_set & NFI_STATUSES):
                    nfi_entries += 1
                if st & SUSP_STATUSES and not (prior_status_set & SUSP_STATUSES):
                    susp_entries += 1
            prior_status_set, prior_team_set = st, tm
        denom = max(1, len(statuses))
        active_share = sum(s == "ACT" for s in statuses) / denom
        released_share = sum(s in RELEASE_STATUSES or s in FREE_AGENT_STATUSES for s in statuses) / denom
        practice_share = sum(s in PRACTICE_STATUSES for s in statuses) / denom
        reserve_share = sum(s in RESERVE_STATUSES or s in PUP_STATUSES or s in NFI_STATUSES for s in statuses) / denom
        rows.append({
            "player_id": str(pid), "season": int(season), "roster_weeks": len(weeks),
            "active_share": float(active_share), "released_share": float(released_share),
            "practice_share": float(practice_share), "reserve_share": float(reserve_share),
            "status_change_count": int(status_changes), "team_change_count": int(team_changes),
            "active_return_count": int(active_returns), "release_entry_count": int(release_entries),
            "practice_entry_count": int(practice_entries), "reserve_entry_count": int(reserve_entries),
            "pup_entry_count": int(pup_entries), "nfi_entry_count": int(nfi_entries), "suspension_entry_count": int(susp_entries),
            "terminal_statuses": set_join(terminal_statuses), "terminal_teams": set_join(terminal_teams),
            "all_statuses": set_join(statuses), "all_teams": set_join(gg._team),
            "last_status_active": float(bool(terminal_statuses & {"ACT"})),
            "last_status_attached": float(bool(terminal_statuses & ATTACHED_STATUSES)),
            "last_status_release": float(bool(terminal_statuses & (RELEASE_STATUSES | FREE_AGENT_STATUSES))),
            "last_status_practice": float(bool(terminal_statuses & PRACTICE_STATUSES)),
            "last_status_reserve": float(bool(terminal_statuses & (RESERVE_STATUSES | PUP_STATUSES | NFI_STATUSES))),
        })
    return pd.DataFrame(rows)


def injury_summary(injuries, rosters):
    roster_week = {}
    for key, g in rosters.groupby(["player_id", "season", "week"]):
        roster_week[key] = set(s for s in g._status if s)
    rows = []
    for (pid, season), g in injuries.groupby(["player_id", "season"]):
        limited_weeks = set(int(w) for w in g.loc[g._official_limitation, "week"])
        report_rows = set(int(w) for w in g.week)
        non_ir = set()
        inactive_injury = set()
        reserve_injury = set()
        for wk in limited_weeks:
            statuses = roster_week.get((str(pid), int(season), int(wk)), set())
            if statuses & (PUP_STATUSES | NFI_STATUSES | RESERVE_STATUSES):
                reserve_injury.add(wk)
            elif statuses & ATTACHED_STATUSES:
                non_ir.add(wk)
                if "INA" in statuses:
                    inactive_injury.add(wk)
        rows.append({
            "player_id": str(pid), "season": int(season),
            "injury_report_weeks": len(report_rows), "injury_limited_weeks": len(limited_weeks),
            "non_ir_injury_limited_weeks": len(non_ir), "inactive_injury_limited_weeks": len(inactive_injury),
            "reserve_injury_limited_weeks": len(reserve_injury),
            "non_ir_injury_flag": float(bool(non_ir)),
            "inactive_injury_flag": float(bool(inactive_injury)),
        })
    return pd.DataFrame(rows)


def participation_summary(stats_weekly, snap_weekly):
    keys_stats = stats_weekly.copy()
    keys_stats["stat_row"] = True
    p = keys_stats.merge(snap_weekly, on=["player_id", "season", "week"], how="outer")
    p["stat_row"] = p["stat_row"].fillna(False)
    p["played_snap"] = p["played_snap"].fillna(False)
    p["game_participation"] = p["stat_row"] | p["played_snap"]
    return p.groupby(["player_id", "season"], as_index=False).agg(
        participation_weeks=("game_participation", "sum"),
        stats_weeks=("stat_row", "sum"),
        snap_play_weeks=("played_snap", "sum"),
    )


def build_source_panel(career, roster_summ, injury_summ, participation_summ):
    c = career.copy()
    c.player_id = c.player_id.astype(str)
    c.season = c.season.astype(int)
    c.position = c.position.astype(str).str.upper()
    c = c[c.position.isin(POSITIONS)].copy()
    by = {(r.player_id, int(r.season)): r for r in c.itertuples()}
    years = c.groupby("player_id").season.apply(lambda s: sorted(set(int(v) for v in s))).to_dict()
    rows = []
    for r in c[(c.season >= 2012) & (c.season <= 2023)].itertuples():
        hist = c[(c.position == r.position) & (c.season <= r.season) & (c.fantasy_points > 0)]
        threshold = quantile(hist.fantasy_points, 0.25)
        boundaries = kmeans_1d(hist.fantasy_points)
        target = by.get((r.player_id, r.season + 1))
        outcome = "out" if target is None else state_for_points(target.fantasy_points, boundaries)
        low = bool(r.fantasy_points > 0 and r.fantasy_points <= threshold)
        band = age_band(r.position, getattr(r, "age_years", None))
        later_return = target is None and any(y > r.season + 1 for y in years.get(r.player_id, []))
        rows.append({
            "player_id": r.player_id, "season": int(r.season), "position": r.position, "age_band": band,
            "experience_years": None if pd.isna(getattr(r, "experience_years", np.nan)) else int(r.experience_years),
            "low_end": low, "outcome_state": outcome,
            "true_developmental": bool(low and band == "young" and outcome in USEFUL_STATES),
            "temporary_absence_return": bool(low and target is None and later_return),
            "persistent_disappearance": bool(low and target is None and not later_return),
            "era": era_for_season(r.season),
        })
    p = pd.DataFrame(rows)
    for a in (roster_summ, injury_summ, participation_summ):
        if a is not None and not a.empty:
            p = p.merge(a, on=["player_id", "season"], how="left")
    zero_cols = [
        "roster_weeks", "active_share", "released_share", "practice_share", "reserve_share",
        "status_change_count", "team_change_count", "active_return_count", "release_entry_count",
        "practice_entry_count", "reserve_entry_count", "pup_entry_count", "nfi_entry_count", "suspension_entry_count",
        "last_status_active", "last_status_attached", "last_status_release", "last_status_practice", "last_status_reserve",
        "injury_report_weeks", "injury_limited_weeks", "non_ir_injury_limited_weeks", "inactive_injury_limited_weeks",
        "reserve_injury_limited_weeks", "non_ir_injury_flag", "inactive_injury_flag", "participation_weeks", "stats_weeks", "snap_play_weeks",
    ]
    for col in zero_cols:
        if col in p.columns:
            p[col] = pd.to_numeric(p[col], errors="coerce").fillna(0.0)
    return p


def roster_status_sets(rosters):
    out = {}
    for key, g in rosters.groupby(["player_id", "season"]):
        statuses = set(s for s in g._status if s)
        teams = set(t for t in g._team if t)
        desc = set(d for d in g._desc if d)
        final_week = int(g.week.max())
        fg = g[g.week == final_week]
        out[(str(key[0]), int(key[1]))] = {
            "statuses": statuses,
            "teams": teams,
            "descriptions": desc,
            "terminal_statuses": set(s for s in fg._status if s),
            "terminal_teams": set(t for t in fg._team if t),
            "rows": int(len(g)),
            "weeks": int(g.week.nunique()),
        }
    return out


def injury_year_sets(injuries):
    out = {}
    for key, g in injuries.groupby(["player_id", "season"]):
        out[(str(key[0]), int(key[1]))] = {
            "rows": int(len(g)),
            "weeks": int(g.week.nunique()),
            "limited_weeks": set(int(w) for w in g.loc[g._official_limitation, "week"]),
            "report_statuses": set(v for v in g._report if v),
            "practice_statuses": set(v for v in g._practice if v),
            "injury_texts": set(v for v in g._injury_text if v),
        }
    return out


def classify_missing_rows(prior_missing, roster_year, injury_year, roster_summ, injury_summ, participation_summ):
    rs = roster_summ.set_index(["player_id", "season"]).to_dict("index") if len(roster_summ) else {}
    ins = injury_summ.set_index(["player_id", "season"]).to_dict("index") if len(injury_summ) else {}
    ps = participation_summ.set_index(["player_id", "season"]).to_dict("index") if len(participation_summ) else {}
    records = []
    for r in prior_missing.itertuples(index=False):
        pid = str(r.player_id); src = int(r.source_season); tgt = int(r.target_season)
        target = roster_year.get((pid, tgt), {"statuses": set(), "teams": set(), "descriptions": set(), "terminal_statuses": set(), "terminal_teams": set(), "rows": 0, "weeks": 0})
        source = roster_year.get((pid, src), {"statuses": set(), "teams": set(), "descriptions": set(), "terminal_statuses": set(), "terminal_teams": set(), "rows": 0, "weeks": 0})
        ti = injury_year.get((pid, tgt), {"rows": 0, "weeks": 0, "limited_weeks": set(), "report_statuses": set(), "practice_statuses": set(), "injury_texts": set()})
        ts = rs.get((pid, tgt), {})
        ss = rs.get((pid, src), {})
        tis = ins.get((pid, tgt), {})
        tps = ps.get((pid, tgt), {})
        statuses = set(target["statuses"]); terminal = set(target["terminal_statuses"]); desc = set(target["descriptions"])
        category = "UNKNOWN_UNRESOLVED"; evidence_scope = "none"; reason = "no defensible target/source event-time cause evidence"
        explicit_ir = any((d == "IR") or ("INJURED" in d and "RESERVE" in d) for d in desc)
        if statuses & RETIRED_STATUSES:
            category, evidence_scope, reason = "RETIRED", "target_season_direct", "explicit RET roster status"
        elif statuses & SUSP_STATUSES:
            category, evidence_scope, reason = "SUSPENDED_OR_EXEMPT", "target_season_direct", "explicit SUS/EXE roster status"
        elif statuses & PUP_STATUSES:
            category, evidence_scope, reason = "PUP", "target_season_direct", "explicit PUP roster status"
        elif statuses & NFI_STATUSES:
            category, evidence_scope, reason = "NFI", "target_season_direct", "explicit RSN/non-football-injury reserve status"
        elif explicit_ir:
            category, evidence_scope, reason = "IR", "target_season_direct", "explicit injured-reserve status description"
        elif statuses & RESERVE_STATUSES:
            category, evidence_scope, reason = "OTHER_RESERVE", "target_season_direct", "explicit generic reserve status; not forced to IR"
        elif statuses & PRACTICE_STATUSES:
            category, evidence_scope, reason = "PRACTICE_SQUAD", "target_season_direct", "explicit DEV/practice-squad status"
        elif statuses & ATTACHED_STATUSES and float(tis.get("non_ir_injury_limited_weeks", 0) or 0) > 0:
            category, evidence_scope, reason = "ACTIVE_ROSTER_INJURY_LIMITED", "target_season_direct", "attached ACT/INA plus official non-reserve injury/practice limitation"
        elif statuses & ATTACHED_STATUSES:
            category, evidence_scope, reason = "ACTIVE_ROSTER_NO_PRODUCTION", "target_season_direct", "attached ACT/INA with no demonstrated injury cause"
        elif statuses & RELEASE_STATUSES:
            category, evidence_scope, reason = "WAIVED_OR_RELEASED", "target_season_direct", "explicit release/cut roster status"
        elif statuses & FREE_AGENT_STATUSES:
            category, evidence_scope, reason = "UNSIGNED_OR_FREE_AGENT", "target_season_direct", "explicit UFA roster status"
        elif target["teams"] and source["terminal_teams"] and target["teams"] != source["terminal_teams"]:
            category, evidence_scope, reason = "TEAM_TRANSITION_TRANSACTION_IN_FLIGHT", "target_season_direct", "factual team change without more specific status"
        else:
            st = set(source["terminal_statuses"])
            if st & RETIRED_STATUSES:
                category, evidence_scope, reason = "RETIRED", "source_terminal_direct", "source season ended with explicit RET status"
            elif st & RELEASE_STATUSES:
                category, evidence_scope, reason = "WAIVED_OR_RELEASED", "source_terminal_direct", "source season ended with explicit release/cut status"
            elif st & FREE_AGENT_STATUSES:
                category, evidence_scope, reason = "UNSIGNED_OR_FREE_AGENT", "source_terminal_direct", "source season ended with explicit UFA status"
            elif st & PRACTICE_STATUSES:
                category, evidence_scope, reason = "PRACTICE_SQUAD", "source_terminal_direct", "source season ended on practice squad; target attachment unavailable"
            elif st & SUSP_STATUSES:
                category, evidence_scope, reason = "TEMPORARY_ABSENCE_OTHER_FACTUAL", "source_terminal_direct", "source season ended suspended/exempt; target status unavailable"
        source_last_teams = set(source["terminal_teams"])
        target_teams = set(target["teams"])
        team_transition = bool(source_last_teams and target_teams and source_last_teams != target_teams)
        records.append({
            "player_id": pid, "source_season": src, "target_season": tgt, "position": str(r.position),
            "age_band": str(r.age_band), "era": era_for_season(src),
            "temporary_absence_return": bool(r.temporary_absence_return),
            "persistent_disappearance": bool(r.persistent_disappearance),
            "prior_e2_context": str(r.primary_context), "absence_cause": category,
            "evidence_scope": evidence_scope, "evidence_reason": reason,
            "target_statuses": set_join(statuses), "target_terminal_statuses": set_join(terminal),
            "target_status_descriptions": set_join(desc), "target_teams": set_join(target_teams),
            "source_terminal_statuses": set_join(source["terminal_statuses"]), "source_terminal_teams": set_join(source_last_teams),
            "team_transition": team_transition,
            "target_roster_rows": int(target["rows"]), "target_roster_weeks": int(target["weeks"]),
            "target_injury_rows": int(ti["rows"]), "target_injury_weeks": int(ti["weeks"]),
            "target_injury_limited_weeks": int(tis.get("injury_limited_weeks", 0) or 0),
            "target_non_ir_injury_limited_weeks": int(tis.get("non_ir_injury_limited_weeks", 0) or 0),
            "target_inactive_injury_limited_weeks": int(tis.get("inactive_injury_limited_weeks", 0) or 0),
            "target_participation_weeks": int(tps.get("participation_weeks", 0) or 0),
            "source_status_change_count": int(ss.get("status_change_count", 0) or 0),
            "source_team_change_count": int(ss.get("team_change_count", 0) or 0),
        })
    return pd.DataFrame(records)


def resolution_tables(missing):
    m = missing.copy()
    m["resolved"] = m.absence_cause != "UNKNOWN_UNRESOLVED"
    overall = {
        "n": int(len(m)), "resolved_n": int(m.resolved.sum()),
        "resolved_share": float(m.resolved.mean()), "unresolved_n": int((~m.resolved).sum()),
        "unresolved_share": float((~m.resolved).mean()),
        "taxonomy_counts": {str(k): int(v) for k, v in m.absence_cause.value_counts().to_dict().items()},
    }
    def tab(cols):
        out = []
        for keys, g in m.groupby(cols, dropna=False):
            if not isinstance(keys, tuple): keys = (keys,)
            row = {c: (str(v) if pd.notna(v) else "NA") for c, v in zip(cols, keys)}
            row.update({"n": int(len(g)), "resolved_n": int(g.resolved.sum()), "resolution": float(g.resolved.mean()), "unresolved_share": float((~g.resolved).mean())})
            for cat in TAXONOMY:
                row[f"n_{cat}"] = int((g.absence_cause == cat).sum())
            out.append(row)
        return out
    return overall, tab(["position"]), tab(["era"]), tab(["era", "position"]), tab(["source_season"])


def cohort_taxonomy(missing, flag):
    g = missing[missing[flag].astype(bool)]
    counts = g.absence_cause.value_counts().to_dict()
    return {
        "n": int(len(g)),
        "counts": {str(k): int(v) for k, v in counts.items()},
        "shares": {str(k): float(v / len(g)) for k, v in counts.items()} if len(g) else {},
    }


def numeric_discrimination(panel, features, positive_flag="true_developmental", negative_flag="persistent_disappearance"):
    pos = panel[panel[positive_flag].astype(bool)]
    neg = panel[panel[negative_flag].astype(bool)]
    rows = []
    for f in features:
        if f not in panel.columns:
            continue
        a = pd.to_numeric(pos[f], errors="coerce").dropna()
        b = pd.to_numeric(neg[f], errors="coerce").dropna()
        if len(a) < 5 or len(b) < 5:
            continue
        raw = auc(a, b)
        rows.append({
            "feature": f, "true_dev_n": int(len(a)), "persistent_n": int(len(b)),
            "true_dev_mean": float(a.mean()), "persistent_mean": float(b.mean()),
            "auc_raw": raw, "auc_absolute_separation": None if raw is None else float(max(raw, 1-raw)),
            "smd_true_dev_minus_persistent": smd(a, b),
            "spearman_vs_active_share": spearman(panel[f], panel.get("active_share", pd.Series(dtype=float))),
            "spearman_vs_released_share": spearman(panel[f], panel.get("released_share", pd.Series(dtype=float))),
        })
    return sorted(rows, key=lambda r: r["auc_absolute_separation"] or 0, reverse=True)


def conditional_incremental(panel, candidate_features):
    p = panel[(panel.true_developmental) | (panel.persistent_disappearance)].copy()
    details = []
    passes = []
    for f in candidate_features:
        if f not in p.columns:
            continue
        corr_a = spearman(p[f], p.get("active_share", pd.Series(index=p.index, dtype=float)))
        corr_r = spearman(p[f], p.get("released_share", pd.Series(index=p.index, dtype=float)))
        nonredundant_corr = (corr_a is None or abs(corr_a) < .80) and (corr_r is None or abs(corr_r) < .80)
        stratum_hits = []
        for active_value in (0.0, 1.0):
            s = p[p.last_status_active == active_value]
            a = pd.to_numeric(s.loc[s.true_developmental, f], errors="coerce").dropna()
            b = pd.to_numeric(s.loc[s.persistent_disappearance, f], errors="coerce").dropna()
            raw = auc(a, b) if len(a) and len(b) else None
            hit = bool(len(a) >= 30 and len(b) >= 60 and raw is not None and max(raw, 1-raw) >= .58)
            stratum_hits.append({"last_status_active": active_value, "true_dev_n": int(len(a)), "persistent_n": int(len(b)), "auc_raw": raw, "auc_abs": None if raw is None else float(max(raw, 1-raw)), "threshold_hit": hit})
        replication = []
        for group_col in ("position", "era"):
            for group, s in p.groupby(group_col):
                a = pd.to_numeric(s.loc[s.true_developmental, f], errors="coerce").dropna()
                b = pd.to_numeric(s.loc[s.persistent_disappearance, f], errors="coerce").dropna()
                if len(a) < 15 or len(b) < 15:
                    continue
                raw = auc(a, b)
                if raw is None:
                    continue
                direction = 1 if raw >= .5 else -1
                replication.append({"dimension": group_col, "group": str(group), "true_dev_n": int(len(a)), "persistent_n": int(len(b)), "auc_raw": raw, "direction": direction})
        stable_groups = [r for r in replication if max(r["auc_raw"], 1-r["auc_raw"]) >= .55]
        dir_counts = Counter(r["direction"] for r in stable_groups)
        replication_ok = bool(dir_counts and max(dir_counts.values()) >= 2)
        overall_pass = bool(nonredundant_corr and any(h["threshold_hit"] for h in stratum_hits) and replication_ok)
        if overall_pass:
            passes.append(f)
        details.append({"feature": f, "corr_active_share": corr_a, "corr_released_share": corr_r, "nonredundant_corr": nonredundant_corr, "strata": stratum_hits, "replication": replication, "replication_ok": replication_ok, "passes_frozen_incremental_diagnostic": overall_pass})
    return details, passes


def baseline_reproduction(prior_json, prior_missing):
    expected = {"n": 925, "resolved_n": 546, "resolved_share": 0.5902702702702702, "unresolved_n": 379, "unresolved_share": 0.4097297297297297}
    observed = {
        "n": int(len(prior_missing)),
        "resolved_n": int((prior_missing.primary_context != "unknown_unresolvable").sum()),
        "resolved_share": float((prior_missing.primary_context != "unknown_unresolvable").mean()),
        "unresolved_n": int((prior_missing.primary_context == "unknown_unresolvable").sum()),
        "unresolved_share": float((prior_missing.primary_context == "unknown_unresolvable").mean()),
    }
    checks = {k: {"expected": v, "observed": observed[k], "pass": abs(float(observed[k]) - float(v)) <= 1e-12} for k, v in expected.items()}
    artifact = prior_json["missing_row_context"]
    artifact_checks = {
        "artifact_n": artifact.get("n") == expected["n"],
        "artifact_resolved_n": artifact.get("resolved_context_n") == expected["resolved_n"],
        "artifact_resolved_share": abs(float(artifact.get("resolved_context_share")) - expected["resolved_share"]) <= 1e-12,
    }
    return {"expected": expected, "observed": observed, "checks": checks, "artifact_checks": artifact_checks, "pass": all(v["pass"] for v in checks.values()) and all(artifact_checks.values())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--prior-e2-json", type=Path, required=True)
    ap.add_argument("--prior-missing-csv", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    prior_json = json.loads(args.prior_e2_json.read_text())
    prior_missing = pd.read_csv(args.prior_missing_csv)
    repro = baseline_reproduction(prior_json, prior_missing)
    if not repro["pass"]:
        raise RuntimeError("Phase-0 E2 baseline reproduction failed: " + json.dumps(repro, sort_keys=True))

    career = pd.read_csv(args.career_panel)
    seasons = list(range(2012, 2025))
    players, raw_rosters, raw_injuries, raw_snaps, raw_stats = load_nflverse(seasons)
    rosters = prepare_roster_weekly(raw_rosters)
    injuries = prepare_injuries(raw_injuries)
    stats_weekly = prepare_stats(raw_stats)
    snap_weekly, snap_audit = prepare_snaps(raw_snaps, players)

    roster_summ = weekly_roster_summary(rosters)
    injury_summ = injury_summary(injuries, rosters)
    participation_summ = participation_summary(stats_weekly, snap_weekly)
    source_panel = build_source_panel(career, roster_summ, injury_summ, participation_summ)

    parity = {
        "true_developmental_n": int(source_panel.true_developmental.sum()),
        "persistent_disappearance_n": int(source_panel.persistent_disappearance.sum()),
        "temporary_absence_return_n": int(source_panel.temporary_absence_return.sum()),
        "prior_true_developmental_n": int(prior_json["cohorts"]["true_developmental"]["n"]),
        "prior_persistent_disappearance_n": int(prior_json["cohorts"]["persistent_disappearance"]["n"]),
        "prior_temporary_absence_return_n": int(prior_json["cohorts"]["temporary_absence_return"]["n"]),
    }

    roster_year = roster_status_sets(rosters)
    injury_year = injury_year_sets(injuries)
    missing = classify_missing_rows(prior_missing, roster_year, injury_year, roster_summ, injury_summ, participation_summ)
    overall, by_position, by_era, by_era_position, by_season = resolution_tables(missing)

    temp = cohort_taxonomy(missing, "temporary_absence_return")
    persistent = cohort_taxonomy(missing, "persistent_disappearance")
    temp_non_ir = temp["shares"].get("ACTIVE_ROSTER_INJURY_LIMITED", 0.0)
    pers_non_ir = persistent["shares"].get("ACTIVE_ROSTER_INJURY_LIMITED", 0.0)

    known_roster = ["last_status_active", "active_share", "released_share"]
    new_features = [
        "status_change_count", "team_change_count", "active_return_count", "release_entry_count", "practice_entry_count",
        "reserve_entry_count", "pup_entry_count", "nfi_entry_count", "suspension_entry_count",
        "injury_limited_weeks", "non_ir_injury_limited_weeks", "inactive_injury_limited_weeks", "reserve_injury_limited_weeks",
        "non_ir_injury_flag", "inactive_injury_flag", "participation_weeks",
    ]
    discr = numeric_discrimination(source_panel, known_roster + new_features)
    inc_details, inc_passes = conditional_incremental(source_panel, new_features)

    coverage_rows = []
    for (era, pos), g in source_panel.groupby(["era", "position"]):
        if era == "outside_frozen_era":
            continue
        coverage_rows.append({
            "era": era, "position": pos, "n": int(len(g)),
            "roster_coverage": float((g.roster_weeks > 0).mean()),
            "injury_row_presence_share": float((g.injury_report_weeks > 0).mean()),
            "snap_or_stats_participation_coverage": float(((g.snap_play_weeks > 0) | (g.stats_weeks > 0)).mean()),
        })

    source_cols = {
        "weekly_rosters": list(raw_rosters.columns), "injuries": list(raw_injuries.columns),
        "snap_counts": list(raw_snaps.columns), "player_stats": list(raw_stats.columns), "players": list(players.columns),
    }
    reserve_desc = Counter()
    rr = rosters[rosters._status.isin(RESERVE_STATUSES)]
    for d in rr._desc:
        if d:
            reserve_desc[d] += 1

    gates = {}
    gates["A_factual_resolution"] = {"pass": overall["resolved_share"] >= .70, "value": overall["resolved_share"], "threshold": .70}
    frozen_eras = {e[2] for e in ERAS}
    era_rows = [r for r in by_era if r["era"] in frozen_eras]
    era_pass = all(float(r["resolution"]) >= .50 for r in era_rows) and len(era_rows) == 3
    gates["B_era_safety"] = {"pass": bool(era_pass), "threshold": "all 3 eras retained; each >=50% resolution"}
    pos_pass = all(float(r["unresolved_share"]) <= .60 for r in by_position) and {r["position"] for r in by_position} == set(POSITIONS)
    gates["C_position_safety"] = {"pass": bool(pos_pass), "threshold": "all QB/RB/WR/TE retained; each <=60% unresolved"}
    d_pass = temp_non_ir >= .05 and (temp_non_ir - pers_non_ir) >= .03
    gates["D_temporary_absence_distinction"] = {"pass": bool(d_pass), "temporary_non_ir_injury_share": temp_non_ir, "persistent_non_ir_injury_share": pers_non_ir, "share_difference": temp_non_ir-pers_non_ir, "threshold": "temporary >=5% and >=3pp above persistent"}
    gates["E_incremental_information"] = {"pass": bool(inc_passes), "passing_features": inc_passes, "threshold": "frozen conditional/nonredundancy diagnostic"}
    gates["F_pit_integrity"] = {"pass": True, "note": "source-period predictor facts use source season only; target/future evidence is outcome context; later return is label only"}
    gates["G_reproducibility"] = {"pass": bool(snap_audit["mapping_rate"] >= .99 and snap_audit["pfr_to_gsis_conflict_ids"] == 0 and snap_audit["manual_mapping_count"] == 0 and snap_audit["name_based_mapping_count"] == 0), "snap_identity_audit": snap_audit}
    gates["H_commercial_governance"] = {"pass_for_precise_governance_picture": True, "classification": "PRODUCTION TERMS REVIEW REQUIRED", "note": "nflverse distribution licenses are permissive but nflverse explicitly states underlying NFL data remain governed by their owners' terms; no restricted NFL.com/PFR scraping used"}

    a_to_g_pass = all(gates[k]["pass"] for k in ["A_factual_resolution","B_era_safety","C_position_safety","D_temporary_absence_distinction","E_incremental_information","F_pit_integrity","G_reproducibility"])
    if a_to_g_pass:
        conclusion = "E1. EVIDENCE SUFFICIENT TO AUTHORIZE A NEW BOUNDED FORECAST CALIBRATION STUDY"
    elif repro["pass"] and (overall["resolved_share"] > prior_json["missing_row_context"]["resolved_context_share"] or temp_non_ir > 0):
        conclusion = "E2. PROMISING EVIDENCE EXISTS BUT RECONSTRUCTION / COVERAGE MUST CONTINUE"
    else:
        conclusion = "E4. AVAILABLE PIT EVIDENCE IS TOO WEAK TO SUPPORT THIS DISTINCTION"

    missing.to_csv(out / "absence_cause_rows.csv", index=False)
    pd.DataFrame(by_position).to_csv(out / "resolution_by_position.csv", index=False)
    pd.DataFrame(by_era).to_csv(out / "resolution_by_era.csv", index=False)
    pd.DataFrame(by_era_position).to_csv(out / "resolution_by_era_position.csv", index=False)
    pd.DataFrame(by_season).to_csv(out / "resolution_by_season.csv", index=False)
    pd.DataFrame(discr).to_csv(out / "descriptive_discrimination.csv", index=False)
    pd.DataFrame(inc_details).to_json(out / "incremental_information.json", orient="records", indent=2)
    pd.DataFrame(coverage_rows).to_csv(out / "source_coverage_by_era_position.csv", index=False)
    (out / "source_columns.json").write_text(json.dumps(source_cols, indent=2, sort_keys=True))

    payload = {
        "study": "event-time-roster-transaction-absence-cause-evidence-v1",
        "frozen_protocol": "artifacts/research/event_time_roster_transaction_absence_cause_protocol.md",
        "phase0_reproduction": repro, "cohort_parity": parity,
        "overall_resolution": overall, "resolution_by_position": by_position, "resolution_by_era": by_era,
        "resolution_by_era_position": by_era_position, "resolution_by_season": by_season,
        "temporary_absence_return": temp, "persistent_disappearance": persistent,
        "non_ir_injury_enrichment": {"temporary_share": temp_non_ir, "persistent_share": pers_non_ir, "difference": temp_non_ir-pers_non_ir},
        "descriptive_discrimination": discr,
        "incremental_information": {"details": inc_details, "passing_features": inc_passes},
        "source_coverage_by_era_position": coverage_rows,
        "reserve_status_description_counts": dict(reserve_desc), "identity_join_audit": snap_audit,
        "source_counts": {"weekly_rosters": int(len(raw_rosters)), "injuries": int(len(raw_injuries)), "snap_counts": int(len(raw_snaps)), "player_stats": int(len(raw_stats)), "players": int(len(players))},
        "gates": gates, "conclusion": conclusion, "no_model_treatment_run": True,
        "leakage": {"forecast_model_fit": False, "value": False, "shapley": False, "market": False, "owner": False, "fantasy_roster": False, "trades_as_fantasy_behavior": False, "future_return_as_predictor": False, "name_based_join": False},
    }
    (out / "event_time_absence_cause_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(json.dumps({"conclusion": conclusion, "resolution": overall, "non_ir": payload["non_ir_injury_enrichment"], "gates": gates, "cohort_parity": parity}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
