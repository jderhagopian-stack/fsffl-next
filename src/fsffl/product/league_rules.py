"""Product contracts for personal league rules; model execution stays upstream."""
from __future__ import annotations

from typing import Annotated
from pydantic import Field

from fsffl.state.account_rules import (
    AccountRuleSettings, DraftOrderSettings, LeagueRuleChanges, apply_account_rules, provider_rule_state,
)
from fsffl.state.models import FrozenModel
from fsffl.state.draft_order_policy import resolve_draft_order_policy
from fsffl.team_utility.future_pick import compile_supported_future_pick_policy
from .scenario_cache import ScenarioComputationStage, run_progressive_scenario_simulation
from .runtime import forecast_input_fingerprint, replay_live_forecast_evidence_for_state


class LeagueRulesRequest(FrozenModel):
    expected_state_id: Annotated[str, Field(min_length=1, max_length=128)]
    expected_revision: Annotated[str, Field(max_length=128)] | None = None
    changes: LeagueRuleChanges = LeagueRuleChanges()
    draft_order: DraftOrderSettings | None = None


class LeagueRulesPreviewRequest(LeagueRulesRequest):
    scenario_stage: ScenarioComputationStage = ScenarioComputationStage.PROVISIONAL


def league_rules_payload(runtime, settings_store, user_id):
    state = runtime.league_state
    if state is None:
        raise ValueError("Connect a league to view its rules.")
    provider = provider_rule_state(state)
    settings = settings_store.get(user_id, state.league.league_id, state.league.season)
    conflicts = []
    if settings and settings.provider_rules_at_save:
        for name in settings.changes.model_dump(exclude_none=True):
            if getattr(provider.league.rules, name) != getattr(settings.provider_rules_at_save, name):
                conflicts.append(name)
    policy = resolve_draft_order_policy(
        state.draft_order_policies, league_id=state.league.league_id,
        draft_season=state.league.season + 1, as_of=state.as_of,
    )
    supported = True
    try:
        compile_supported_future_pick_policy(
            policy, draft_season=state.league.season + 1, team_count=state.league.rules.team_count,
            playoff_team_count=state.league.rules.playoff_team_count,
        )
    except ValueError:
        supported = False
    return {
        "league_id": state.league.league_id, "league_name": state.league.name,
        "season": state.league.season, "draft_season": state.league.season + 1,
        "state_id": state.state_id, "revision": settings.revision if settings else None,
        "provider_as_of": provider.as_of.isoformat(),
        "provider_rules": provider.league.rules.model_dump(mode="json"),
        "effective_rules": state.league.rules.model_dump(mode="json"),
        "changes": settings.changes.model_dump(mode="json", exclude_none=True) if settings else {},
        "draft_order": settings.draft_order.model_dump(mode="json") if settings and settings.draft_order else None,
        "has_overrides": bool(settings and settings.has_overrides),
        "durable": settings_store.persistence is not None,
        "provider_conflicts": conflicts,
        "draft_order_confirmed": policy is not None,
        "draft_order_description": policy.description if policy else None,
        "draft_order_supported": supported,
        "draft_order_message": (
            "Draft positions cannot yet be projected under this rule."
            if not supported else "Using your draft-order rule." if policy else
            "Draft order needs clarification. Positions are currently estimated from record and playoff finish."
        ),
        "settings_applied": (
            not settings or not settings.has_overrides or
            bool(state.rule_configuration and state.rule_configuration.revision == settings.revision)
        ),
    }


def rule_change_summary(before, after):
    labels = {"roster_size": "Active roster limit", "taxi_size": "Taxi slots", "ir_size": "IR slots",
              "rookie_draft_rounds": "Rookie draft rounds", "lineup": "Starting lineup", "scoring": "Scoring",
              "playoff_team_count": "Playoff teams", "playoff_start_week": "Playoffs start",
              "fantasy_regular_season_end_week": "Regular season ends"}
    rows = []
    for name, label in labels.items():
        old = before.league.rules.model_dump(mode="json")[name]
        new = after.league.rules.model_dump(mode="json")[name]
        if old != new:
            rows.append({"field": name, "label": label, "before": old, "after": new})
    if before.draft_order_policies != after.draft_order_policies:
        rows.append({"field": "draft_order", "label": "Rookie draft order",
                     "before": "Previous draft-order setting", "after": "Proposed draft-order setting"})
    return rows


def build_rule_what_if(runtime, candidate: AccountRuleSettings, *, simulation_loader,
                       stage=ScenarioComputationStage.PROVISIONAL):
    state = runtime.league_state
    changed = apply_account_rules(state, candidate, mode="what_if")
    payload = {"scenario_kind": "league_rules", "saved": False,
               "state_id_before": state.state_id, "state_id_after": changed.state_id,
               "changes": rule_change_summary(state, changed), "teams": [],
               "draft_order_supported": candidate.draft_order is None or candidate.draft_order.supported}
    if not payload["changes"]:
        return {**payload, "message": "No rule changes to compare."}
    # Draft-order/roster-capacity changes do not themselves change weekly football
    # outcomes. Do not run Monte Carlo solely to print a zero wins difference.
    competition_fields = {"lineup", "scoring", "playoff_team_count", "playoff_start_week"}
    if not any(row["field"] in competition_fields for row in payload["changes"]):
        return {**payload, "message": (
            "This changes draft-position estimates, not this season's games."
            if any(row["field"] == "draft_order" for row in payload["changes"]) else
            "These limits change roster and trade accounting. No players have been moved or cut."
        )}
    if runtime.forecast_evidence is None or runtime.simulation_analytics is None:
        return {**payload, "message": "Run your league analysis before comparing season outcomes."}
    forecast = runtime.forecast_evidence
    if forecast_input_fingerprint(state) != forecast_input_fingerprint(changed):
        forecast = replay_live_forecast_evidence_for_state(changed, forecast)
    result, hit, computation = run_progressive_scenario_simulation(
        state, changed, forecast, runtime.simulation_analytics,
        simulation_loader=simulation_loader, stage=stage,
    )
    before = {view.team_id: view.utility.competitive_outcome for view in runtime.simulation_analytics.team_views if view.utility}
    names = {team.team_id: team.display_name for team in state.teams}
    teams = []
    for view in result.team_views:
        if view.utility is None or view.team_id not in before:
            continue
        old, new = before[view.team_id], view.utility.competitive_outcome
        teams.append({"team_id": view.team_id, "name": names.get(view.team_id, view.team_id),
                      "before": old.model_dump(mode="json"), "after": new.model_dump(mode="json")})
    return {**payload, "teams": teams, "scenario_cache_hit": hit,
            "scenario_computation": computation.model_dump(mode="json"),
            "message": "What-If only. Your saved rules and league analysis are unchanged."}
