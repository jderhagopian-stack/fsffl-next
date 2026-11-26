from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .models import (
    DraftOrderPolicyEvidence, DraftOrderPolicyParameter, FrozenModel, LeagueRules,
    LeagueRuleConfiguration, LeagueState, LineupRequirement, Provenance, ScoringRule,
)


class LeagueRuleChanges(FrozenModel):
    roster_size: Annotated[int, Field(ge=1, le=100)] | None = None
    taxi_size: Annotated[int, Field(ge=0, le=100)] | None = None
    ir_size: Annotated[int, Field(ge=0, le=100)] | None = None
    rookie_draft_rounds: Annotated[int, Field(ge=0, le=20)] | None = None
    playoff_team_count: Annotated[int, Field(ge=2, le=32)] | None = None
    playoff_start_week: Annotated[int, Field(ge=2, le=18)] | None = None
    lineup: Annotated[tuple[LineupRequirement, ...], Field(max_length=30)] | None = None
    scoring: Annotated[tuple[ScoringRule, ...], Field(max_length=150)] | None = None

    @model_validator(mode="after")
    def unique_coordinates(self):
        for rows, name in ((self.lineup, "slot"), (self.scoring, "stat")):
            if rows is not None and len({getattr(row, name) for row in rows}) != len(rows):
                raise ValueError(f"duplicate {name} settings")
        if self.lineup is not None:
            if sum(row.count for row in self.lineup) > 30:
                raise ValueError("The editable starting lineup supports at most 30 slots.")
            if any(row.slot.value in {"BENCH", "IR", "TAXI"} for row in self.lineup):
                raise ValueError("Bench, IR and taxi are roster limits, not starting lineup positions.")
        if self.scoring is not None:
            from math import isfinite
            if any(not isfinite(row.points) or abs(row.points) > 10_000 for row in self.scoring):
                raise ValueError("scoring points must be finite and within supported bounds")
        return self


class DraftOrderSettings(FrozenModel):
    non_playoff_order: Literal["record", "max_pf", "custom"]
    playoff_order: Literal["elimination", "placement_games", "max_pf", "custom"]
    tiebreak: Literal["record_h2h_points_for", "record", "points_for", "unresolved", "custom"]
    notes: Annotated[str, Field(max_length=1500)] = ""

    @model_validator(mode="after")
    def describe_custom_terms(self):
        if "custom" in (self.non_playoff_order, self.playoff_order, self.tiebreak) and not self.notes.strip():
            raise ValueError("Describe the custom draft-order or tiebreak rule in additional details.")
        return self

    @property
    def supported(self) -> bool:
        return (self.non_playoff_order == "record"
                and self.playoff_order in {"elimination", "placement_games"}
                and self.tiebreak == "record_h2h_points_for")


class AccountRuleSettings(FrozenModel):
    account_scope: str
    league_id: str
    season: int
    revision: str
    saved_at: datetime
    provider_rules_at_save: LeagueRules | None = None
    changes: LeagueRuleChanges = LeagueRuleChanges()
    draft_order: DraftOrderSettings | None = None

    @model_validator(mode="after")
    def validate_saved_at(self):
        if self.saved_at.tzinfo is None:
            raise ValueError("settings saved_at must be timezone-aware")
        return self

    @property
    def has_overrides(self) -> bool:
        return bool(self.changes.model_dump(exclude_none=True) or self.draft_order)


def provider_rule_state(state: LeagueState) -> LeagueState:
    configuration = state.rule_configuration
    if configuration is None:
        return state
    return LeagueState.model_validate({
        **state.model_dump(),
        "league": state.league.model_copy(update={"rules": configuration.provider_rules}),
        "draft_order_policies": configuration.provider_draft_order_policies,
        "as_of": configuration.provider_as_of,
        "rule_configuration": None,
    })


def resolved_rules(provider: LeagueRules, changes: LeagueRuleChanges) -> LeagueRules:
    patch = changes.model_dump(exclude_none=True)
    playoff_changed = any(
        name in patch and patch[name] != getattr(provider, name)
        for name in ("playoff_team_count", "playoff_start_week")
    )
    if playoff_changed and provider.playoff_rules is not None:
        raise ValueError("This league has a specific playoff bracket. Its format cannot yet be edited here.")
    if "playoff_start_week" in patch:
        patch["fantasy_regular_season_end_week"] = patch["playoff_start_week"] - 1
    rules = LeagueRules.model_validate({**provider.model_dump(), **patch})
    if sum(row.count for row in rules.lineup) > rules.roster_size:
        raise ValueError("Starting lineup cannot exceed the active roster limit.")
    if playoff_changed and rules.playoff_team_count not in {2, 4, 6, 8}:
        raise ValueError("The editable standard playoff formats support 2, 4, 6 or 8 teams.")
    return rules


def apply_account_rules(
    state: LeagueState, settings: AccountRuleSettings | None, *, mode: Literal["saved", "what_if"] = "saved",
) -> LeagueState:
    provider = provider_rule_state(state)
    if settings is None or not settings.has_overrides:
        return provider
    if settings.league_id != provider.league.league_id or settings.season != provider.league.season:
        raise ValueError("Personal rules belong to a different league or season.")
    configuration = state.rule_configuration
    if (configuration is not None and configuration.revision == settings.revision
            and configuration.account_scope == settings.account_scope and configuration.mode == mode):
        return state
    rules = resolved_rules(provider.league.rules, settings.changes)
    for field, excluded in (
        ("ir_size", {"IR"}), ("taxi_size", {"TAXI"}), ("roster_size", None),
    ):
        limit = getattr(rules, field)
        if limit >= getattr(provider.league.rules, field):
            continue
        for team in provider.team_states:
            occupied = sum(
                entry.slot.value in excluded if excluded is not None else
                entry.slot.value not in {"IR", "TAXI"}
                for entry in team.roster
            )
            if occupied > limit:
                label = {"ir_size":"IR", "taxi_size":"taxi", "roster_size":"active roster"}[field]
                raise ValueError(f"This reduction needs explicit roster moves: a team holds {occupied} {"player" if occupied == 1 else "players"} for {limit} {label} slots. No players have been moved or cut.")
    policies = provider.draft_order_policies
    if settings.draft_order is not None:
        draft = settings.draft_order
        placement = draft.playoff_order == "placement_games"
        if draft.supported and placement and rules.playoff_team_count != 6:
            raise ValueError("Placement-game draft ordering currently supports six playoff teams.")
        if draft.supported and (rules.playoff_team_count is None or rules.playoff_team_count >= rules.team_count):
            raise ValueError("Draft order requires both playoff and non-playoff teams.")
        from .draft_order_policy import (
            STANDARD_DRAFT_ORDER_MECHANISM_V1, STANDARD_REGULAR_SEASON_TIEBREAK, STANDARD_PLAYOFF_ORDER,
        )
        # Unsupported rules remain explicit evidence. The accepted compiler makes
        # only pick-slot projections unavailable; it must never use record instead.
        parameters = ({
            "non_playoff_tiebreak_policy": STANDARD_REGULAR_SEASON_TIEBREAK,
            "playoff_order_policy": STANDARD_PLAYOFF_ORDER,
            "origin_slot_carries_across_rounds": True,
            "placement_games_affect_order": placement,
            **({"placement_games_policy": "six_team_standard_placement_games_v1"} if placement else {}),
        } if draft.supported else {
            "non_playoff_order": draft.non_playoff_order,
            "playoff_order": draft.playoff_order, "tiebreak": draft.tiebreak,
        })
        season = provider.league.season + 1
        policies = tuple(row for row in policies if row.draft_season != season) + (
            DraftOrderPolicyEvidence(
                league_id=provider.league.league_id, draft_season=season,
                effective_at=settings.saved_at, available_at=settings.saved_at,
                policy_id="account-draft-order", version=settings.revision,
                mechanism=STANDARD_DRAFT_ORDER_MECHANISM_V1 if draft.supported else "account_custom_draft_order_v1",
                description=f"{draft.non_playoff_order}; {draft.playoff_order}; {draft.tiebreak}. {draft.notes}".strip(),
                parameters=tuple(DraftOrderPolicyParameter(name=k, value=v) for k, v in sorted(parameters.items())),
                provenance=Provenance(source="account_league_rules", retrieved_at=settings.saved_at,
                                      effective_at=settings.saved_at, source_version=settings.revision),
            ),
        )
    return LeagueState.model_validate({
        **provider.model_dump(),
        "league": provider.league.model_copy(update={"rules": rules}),
        "as_of": max(provider.as_of, settings.saved_at),
        "draft_order_policies": policies,
        "rule_configuration": LeagueRuleConfiguration(
            account_scope=settings.account_scope, revision=settings.revision, mode=mode,
            provider_rules=provider.league.rules, provider_as_of=provider.as_of,
            provider_draft_order_policies=provider.draft_order_policies,
        ),
    })
