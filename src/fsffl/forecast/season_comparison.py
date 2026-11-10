"""Read-only season comparison built by Forecast during an owned refresh."""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatsSource
from fsffl.state.models import Position, Provenance
from .in_season_orchestration import (
    build_governed_in_season_outlook, canonical_week_window,
    fill_current_ros_fumbles_lost_gaps,
    build_current_ros_fumbles_lost_supplement_observations,
)
from .in_season_runtime import build_in_season_forecasts
from .league_scoring import derive_league_scoring_result
from .models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from .projection_history import career_ros_projection_selector
from .season_rollforward import compose_completed_actuals_with_ros_per_player

SEASON_COMPARISON_VERSION = "season-comparison-v3:shared-participation-exceptions"
POSITIONS = {Position.QB, Position.RB, Position.WR, Position.TE}


class StateBoundStats:
    """The completed-week boundary must agree with canonical State."""
    def __init__(self, state, source):
        self.state, self.source = state, source
        self.latest_actuals_capture = None

    def fetch_nfl_state(self):
        current = self.source.fetch_nfl_state()
        if (current.season != self.state.league.season
                or current.completed_through_week != self.state.completed_through_week):
            raise ValueError("season comparison requires the exact State completed-week boundary")
        return current

    def fetch_week(self, *, season, week):
        if season != self.state.league.season or not 1 <= week <= self.state.completed_through_week:
            raise ValueError("season comparison cannot acquire future or different-season actuals")
        lines = self.source.fetch_week(season=season, week=week)
        captured = max((line.captured_at for line in lines), default=None)
        if captured is not None:
            self.latest_actuals_capture = max(
                captured, self.latest_actuals_capture or captured,
            )
        return lines

    def fetch_season(self, *, season):
        # The accepted fumbles model consumes prior-season factual production.
        if season >= self.state.league.season:
            raise ValueError("fumbles prior must precede the comparison season")
        return self.source.fetch_season(season=season)


def complete_comparison_ros(state, runtime, *, stats_source, completed, as_of):
    """Preserve the ensemble first, then complete permitted single-source gaps.

    This consumer explicitly labels one-source evidence. It does not lower the
    independent-source minimum of the shared ROS or full-season ensembles.
    """
    full, _ = fill_current_ros_fumbles_lost_gaps(
        state, current_runtime=runtime, stats_source=stats_source,
        completed_through_week=completed, as_of=as_of,
    )
    ready = {row.player_id: row for row in full}
    groups = defaultdict(list)
    for row in runtime.source_observations:
        groups[(row.player_id, row.source)].append(row)
    candidates = {}
    for (pid, source), rows in sorted(groups.items()):
        if pid in ready or pid in candidates:
            continue
        scored = derive_league_scoring_result(tuple(rows), rules=state.league.rules)
        if scored.authoritative_forecasts or any(
            tuple(sorted(item.omitted_rule_stats)) == ("fum_lost",)
            for item in scored.partial_forecasts
        ):
            candidates[pid] = tuple(rows)
    if candidates:
        try:
            supplement = build_current_ros_fumbles_lost_supplement_observations(
                state, current_runtime=runtime, stats_source=stats_source,
                completed_through_week=completed, as_of=as_of,
                eligible_player_ids=set(candidates),
            )
        except Exception:
            supplement = ()
        lost = {row.player_id: row for row in supplement}
        for pid, rows in candidates.items():
            if pid not in lost:
                continue  # Never call an incomplete single-source row complete.
            ordinary = tuple(row for row in rows if row.metric != ForecastMetric.FUMBLES_LOST)
            scored = derive_league_scoring_result(
                ordinary, rules=state.league.rules, supplemental_observations=(lost[pid],),
                source="fsffl:single-source-ros-with-first-party-fumbles",
                model_version=SEASON_COMPARISON_VERSION,
            )
            if scored.authoritative_forecasts:
                ready[pid] = scored.authoritative_forecasts[0]
    return runtime.model_copy(update={
        "fantasy_point_forecasts": tuple(ready[pid] for pid in sorted(ready)),
        "partial_fantasy_point_forecasts": tuple(
            row for row in runtime.partial_fantasy_point_forecasts if row.player_id not in ready
        ),
    })


def apply_participation_exceptions(state, result, *, as_of, verified_roles=None):
    """Reuse Intrinsic's accepted eligibility, without importing product code."""
    from .participation import (
        recorded_status_based_zero_ros_evidence, recorded_ytd_only_year_one_evidence,
        recorded_ir_no_projection_year_one_evidence, _unsigned_ytd_override,
    )
    from fsffl.providers.nfl_status_evidence import recorded_nfl_role_receipts
    official = recorded_status_based_zero_ros_evidence(state, as_of=as_of)
    roles = recorded_nfl_role_receipts(state, as_of=as_of)
    roles.update({pid: row for pid, row in (verified_roles or {}).items() if row.captured_at <= as_of})
    ytd = recorded_ytd_only_year_one_evidence(state, as_of=as_of, verified_roles=roles)
    runtime = result.current_runtime
    available = tuple(runtime.source_observations) if runtime is not None else ()
    current_ids = {
        row.player_id for row in runtime.fantasy_point_forecasts
        if row.source != "fsffl:single-source-ros-with-first-party-fumbles"
    } if runtime else set()
    projected_ids = {row.player_id for row in available}
    forward = {row.player_id: row for row in result.forward_forecasts}
    explanations = {}
    start = canonical_week_window(state.league.season, result.completed_through_week + 1)[0]
    end = canonical_week_window(state.league.season, 18)[1]
    for player in state.players:
        if player.position not in POSITIONS:
            continue
        pid = player.player_id
        receipt = _unsigned_ytd_override(pid, roles=roles, receipts=ytd, as_of=as_of)
        unsigned = not player.nfl_team or player.nfl_team.upper() in {"FA", "N/A", "NONE"}
        if unsigned or receipt is not None:
            kind, message, assumption = "unsigned", "No additional production assumed while off an NFL roster.", True
            source = receipt.source if receipt else "canonical-state:no-nfl-team"
            version = receipt.source_version if receipt else SEASON_COMPARISON_VERSION
            observed = receipt.observed_at if receipt else state.as_of
        elif pid in current_ids:
            continue  # Keep complete current projections, as Intrinsic does.
        elif pid in official:
            receipt = official[pid]
            receipt.validate()
            kind, message, assumption = "verified_unavailable", "Recorded season unavailability: no remaining production expected.", False
            source, version, observed = receipt.source, receipt.source_version, receipt.observed_at
        else:
            if pid in projected_ids:
                continue  # IR/role assumptions cannot override available source rows.
            receipt = ytd.get(pid) or recorded_ir_no_projection_year_one_evidence(
                state, player_id=pid, as_of=as_of, available_projection_rows=available,
            )
            if receipt is None:
                continue
            receipt.validate()
            kind = "ir_no_projection" if receipt.source == "fsffl:exact-state-ir-no-projection" else "approved_role"
            message = ("IR with no projection: actuals only; no additional production assumed."
                       if kind == "ir_no_projection" else
                       "Approved roster-status fallback: actuals only; no additional production assumed.")
            assumption = True
            source, version, observed = receipt.source, receipt.source_version, receipt.observed_at
        forward[pid] = ForecastObservation(
            player_id=pid, position=player.position, horizon=ForecastHorizon.REST_OF_SEASON,
            metric=ForecastMetric.FANTASY_POINTS, period_start=start, period_end=end,
            as_of=as_of, distribution=ForecastDistribution(mean=0, stddev=0, p10=0, p50=0, p90=0),
            source="fsffl:no-nfl-team-no-ros" if kind == "unsigned" else f"fsffl:participation-zero-ros:{kind}",
            model_version=version,
            provenance=Provenance(source=source, retrieved_at=observed, effective_at=observed, source_version=version),
        )
        explanations[pid] = {"participation_basis": kind, "participation_reason": message,
            "participation_assumption": assumption, "participation_source": source,
            "participation_source_version": version, "participation_observed_at": observed.isoformat()}
    result.forward_forecasts = tuple(forward[pid] for pid in sorted(forward))
    return explanations


def build_season_comparison(state, *, preseason_forecasts, preseason_as_of=None,
                            stats_source=None, history_store=None, clock=None,
                            fallback_forecasts=None, preseason_basis="original_published_preseason"):
    """Build small player rows; keep actuals and remaining uncertainty separate."""
    live_clock = clock or (lambda: datetime.now(UTC))
    now = live_clock()
    stats = StateBoundStats(state, stats_source or SleeperWeeklyStatsSource())

    def evaluation_clock():
        # Actuals are acquired before the ROS runtime. Its evaluation cutoff
        # must include those observed facts; original provider timestamps stay
        # in provenance. Never freeze the cutoff before network acquisition.
        return max(live_clock(), now, stats.latest_actuals_capture or now)

    def ros_builder(league_state, **kwargs):
        evaluation_cutoff = kwargs["clock"]()
        if history_store is not None:
            kwargs["source_revisions"] = history_store.latest_revisions(
                career_ros_projection_selector(
                    season=state.league.season, completed_through_week=state.completed_through_week,
                    as_of=evaluation_cutoff,
                )
            )
            kwargs["supplement_missing_sources"] = True
        kwargs["allow_undercovered_sources"] = True
        runtime = build_in_season_forecasts(league_state, **kwargs)
        if not runtime.source_observations:
            raise ValueError("no current ROS source evidence; use the labeled preserved prior")
        return complete_comparison_ros(
            state, runtime, stats_source=stats, completed=state.completed_through_week,
            as_of=max(evaluation_cutoff, runtime.evaluation_as_of),
        )

    result = build_governed_in_season_outlook(
        state, preseason_season_forecasts=tuple(
            fallback_forecasts if fallback_forecasts is not None else preseason_forecasts),
        stats_source=stats, clock=evaluation_clock, runtime_builder=ros_builder,
        history_writer=history_store,
    )
    participation = {}
    if result.completed_through_week < 18:
        players_by_id = {player.player_id: player for player in state.players}
        participation_cutoff = max(evaluation_clock(), result.current_runtime.evaluation_as_of
                                   if result.current_runtime is not None else now)
        verified_roles = {}
        # Match the existing live Intrinsic producer's bounded official RLS
        # verification. Historical/injected runs never fetch newer role facts.
        if stats_source is None and clock is None:
            from fsffl.providers.nfl_status_evidence import acquire_official_reserve_role_receipts
            verified_roles = acquire_official_reserve_role_receipts(
                state, evaluation_cutoff=participation_cutoff, allow_current_capture=True,
            )
            if verified_roles:
                participation_cutoff = max(participation_cutoff, *(r.captured_at for r in verified_roles.values()))
        participation = apply_participation_exceptions(
            state, result, as_of=participation_cutoff, verified_roles=verified_roles,
        )
        result.season_outlook, result.season_outlook_failures = compose_completed_actuals_with_ros_per_player(
            completed_actuals=result.completed_actuals, ros_forecasts=result.forward_forecasts,
            season_start=canonical_week_window(state.league.season, 1)[0],
            expected_roster_positions={
                entry.player_id: players_by_id[entry.player_id].position
                for team in state.team_states for entry in team.roster
                if entry.player_id in players_by_id and players_by_id[entry.player_id].position in POSITIONS
            },
        )
    baseline = {row.player_id: row for row in preseason_forecasts
                if row.horizon == ForecastHorizon.SEASON and row.metric == ForecastMetric.FANTASY_POINTS}
    forward = {row.player_id: row for row in result.forward_forecasts}
    outlook = {row.player_id: row for row in result.season_outlook}
    actuals = defaultdict(list)
    season_start, _ = canonical_week_window(state.league.season, 1)
    for row in result.completed_actuals:
        actuals[row.player_id].append(row)
    players = {}
    for player in state.players:
        if player.position not in POSITIONS:
            continue
        pid = player.player_id
        records = sorted(actuals[pid], key=lambda row: row.period_start)
        earned = sum(row.actual for row in records) if records else (0.0 if result.completed_through_week == 0 else None)
        prior, ros, total = baseline.get(pid), forward.get(pid), outlook.get(pid)
        prior_points = prior.distribution.mean if prior is not None else None
        ros_points = ros.distribution.mean if ros is not None else (0.0 if result.completed_through_week == 18 else None)
        total_points = total.distribution.mean if total is not None else None
        weekly = []
        cumulative = 0.0
        points_by_week = {(row.period_start - season_start).days // 7 + 1: row.actual for row in records}
        if records:
            for week in range(1, result.completed_through_week + 1):
                cumulative += points_by_week.get(week, 0.0)
                weekly.append({"week": week, "points": cumulative})
        basis = ros.source if ros is not None else result.evidence_basis
        players[pid] = {
            **participation.get(pid, {}),
            "status": "ready" if total_points is not None else "partial",
            "preseason_points": prior_points, "actual_points": earned,
            "ros_points": ros_points, "outlook_points": total_points,
            "change_from_preseason": total_points - prior_points if total_points is not None and prior_points is not None else None,
            "preseason_as_of": preseason_as_of or (prior.as_of.isoformat() if prior is not None else None),
            "preseason_basis": preseason_basis,
            "completed_through_week": result.completed_through_week,
            "weekly_actuals": weekly, "ros_basis": basis,
            "low_confidence": bool(participation.get(pid, {}).get("participation_assumption")) or "single-source" in basis or "prior" in basis or "no-nfl-team" in basis,
            "ros_p10": ros.distribution.p10 if ros is not None else None,
            "ros_p90": ros.distribution.p90 if ros is not None else None,
            "reason": result.season_outlook_failures.get(pid),
        }
    measured_as_of = max([now] + [row.finalized_at for row in result.completed_actuals]
                          + [row.as_of for row in result.forward_forecasts])
    return {"version": SEASON_COMPARISON_VERSION, "league_state_id": state.state_id,
            "season": state.league.season, "as_of": measured_as_of.isoformat(),
            "completed_through_week": result.completed_through_week, "players": players}
