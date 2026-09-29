from __future__ import annotations

from fsffl.state.models import FrozenModel, LeagueState, Position

from .fumbles_lost_first_party import (
    FirstPartyFumblesLostEvidenceTier,
    FirstPartyFumblesLostSupplement,
)
from .fumbles_lost_first_party_priors import PLAYER_PRIORS
from .fumbles_lost_rolling_authority import (
    NON_MATERIAL_PARTIAL_AUTHORITY,
    FumblesLostProductionTable,
    non_material_partial_passes,
    resolve_fumbles_lost_production_table,
)
from .league_scoring import PartialFantasyPointForecast


_ALLOWED_POSITIONS = frozenset({Position.QB, Position.RB, Position.WR, Position.TE})


class FumblesLostMaterialityAssessment(FrozenModel):
    player_id: str
    position: Position
    completed_through_week: int
    evidence_tier: FirstPartyFumblesLostEvidenceTier
    eligible: bool
    status: str
    event_bound_90: float | None = None
    scoring_points_per_event: float
    impact_bound_90: float | None = None
    supported_fantasy_point_stddev: float
    allowed_impact_90: float | None = None
    reason: str
    contract_version: str


def fumbles_lost_scoring_coefficient(league_state: LeagueState) -> float:
    return sum(
        float(rule.points)
        for rule in league_state.league.rules.scoring
        if rule.stat == "fum_lost"
    )


def _fallback_tier(
    league_state: LeagueState,
    *,
    player_id: str,
    position: Position,
    supplement: FirstPartyFumblesLostSupplement | None,
) -> tuple[FirstPartyFumblesLostEvidenceTier, bool, str]:
    canonical = next(
        (player for player in league_state.players if player.player_id == player_id),
        None,
    )
    if (
        canonical is None
        or canonical.position not in _ALLOWED_POSITIONS
        or canonical.position != position
    ):
        return (
            FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT,
            False,
            "canonical offensive position is missing or conflicting",
        )

    if supplement is not None:
        evidence = next(
            (row for row in supplement.player_evidence if row.player_id == player_id),
            None,
        )
        if evidence is not None:
            return evidence.evidence_tier, True, "supplement evidence tier"
        if player_id in supplement.omitted_player_ids:
            return (
                FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT,
                False,
                "point-model subject was omitted for conflicting evidence",
            )

    prior = PLAYER_PRIORS.get(player_id)
    if prior is None:
        return (
            FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT,
            True,
            "canonical position known but historical identity is unavailable",
        )
    (
        prior_position,
        _historical_gsis_id,
        identity_method,
        accepted_tier,
        history_games,
        _history_opportunities,
        _accepted_current_games,
        _accepted_current_opportunities,
        _accepted_shadow_mean,
        _accepted_shadow_stddev,
    ) = prior
    if str(prior_position) != position.value:
        return (
            FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT,
            False,
            "frozen historical position conflicts with canonical position",
        )
    if str(identity_method) == "unmapped" or str(accepted_tier) == "unmapped":
        return (
            FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT,
            True,
            "canonical position known but frozen identity is light",
        )
    if int(history_games) > 0:
        return (
            FirstPartyFumblesLostEvidenceTier.HISTORY_ONLY,
            True,
            "governed historical role evidence is available",
        )
    if str(accepted_tier) == "current_only":
        return (
            FirstPartyFumblesLostEvidenceTier.CURRENT_ONLY,
            True,
            "frozen evidence population is current-only",
        )
    return (
        FirstPartyFumblesLostEvidenceTier.COLD_START,
        True,
        "no governed historical role evidence is available",
    )


def assess_fumbles_lost_non_material_partial(
    league_state: LeagueState,
    *,
    partial: PartialFantasyPointForecast,
    supported_fantasy_point_stddev: float,
    supplement: FirstPartyFumblesLostSupplement | None,
    production_table: FumblesLostProductionTable | None = None,
) -> FumblesLostMaterialityAssessment:
    table = resolve_fumbles_lost_production_table(
        league_state.league.season,
        table=production_table,
    )
    cutoff = league_state.completed_through_week
    coefficient = fumbles_lost_scoring_coefficient(league_state)
    tier, identity_eligible, tier_reason = _fallback_tier(
        league_state,
        player_id=partial.player_id,
        position=partial.position,
        supplement=supplement,
    )
    contract_version = str(table.payload["materiality_contract"]["contract_version"])  # type: ignore[index]

    if "fum_lost" not in partial.omitted_rule_stats:
        return FumblesLostMaterialityAssessment(
            player_id=partial.player_id,
            position=partial.position,
            completed_through_week=cutoff,
            evidence_tier=tier,
            eligible=False,
            status="MATERIAL_PARTIAL",
            scoring_points_per_event=coefficient,
            supported_fantasy_point_stddev=supported_fantasy_point_stddev,
            reason="FUMBLES_LOST is not the omitted coordinate",
            contract_version=contract_version,
        )
    if coefficient == 0:
        return FumblesLostMaterialityAssessment(
            player_id=partial.player_id,
            position=partial.position,
            completed_through_week=cutoff,
            evidence_tier=tier,
            eligible=False,
            status="MATERIAL_PARTIAL",
            scoring_points_per_event=coefficient,
            supported_fantasy_point_stddev=supported_fantasy_point_stddev,
            reason="league has no active FUMBLES_LOST scoring coefficient",
            contract_version=contract_version,
        )
    if not identity_eligible:
        return FumblesLostMaterialityAssessment(
            player_id=partial.player_id,
            position=partial.position,
            completed_through_week=cutoff,
            evidence_tier=tier,
            eligible=False,
            status="MATERIAL_PARTIAL",
            scoring_points_per_event=coefficient,
            supported_fantasy_point_stddev=supported_fantasy_point_stddev,
            reason=tier_reason,
            contract_version=contract_version,
        )
    if not table.fallback_eligible(cutoff, partial.position, tier.value):
        return FumblesLostMaterialityAssessment(
            player_id=partial.player_id,
            position=partial.position,
            completed_through_week=cutoff,
            evidence_tier=tier,
            eligible=False,
            status="MATERIAL_PARTIAL",
            scoring_points_per_event=coefficient,
            supported_fantasy_point_stddev=supported_fantasy_point_stddev,
            reason=(
                "frozen population eligibility fails closed for this position/cutoff/tier"
            ),
            contract_version=contract_version,
        )

    try:
        event_bound = table.materiality_event_bound(cutoff, partial.position)
    except ValueError as exc:
        return FumblesLostMaterialityAssessment(
            player_id=partial.player_id,
            position=partial.position,
            completed_through_week=cutoff,
            evidence_tier=tier,
            eligible=False,
            status="MATERIAL_PARTIAL",
            scoring_points_per_event=coefficient,
            supported_fantasy_point_stddev=supported_fantasy_point_stddev,
            reason=str(exc),
            contract_version=contract_version,
        )

    passed, impact, allowance = non_material_partial_passes(
        scoring_points_per_event=coefficient,
        event_bound_90=event_bound,
        supported_fantasy_point_stddev=supported_fantasy_point_stddev,
    )
    return FumblesLostMaterialityAssessment(
        player_id=partial.player_id,
        position=partial.position,
        completed_through_week=cutoff,
        evidence_tier=tier,
        eligible=True,
        status=(
            NON_MATERIAL_PARTIAL_AUTHORITY
            if passed
            else "MATERIAL_PARTIAL"
        ),
        event_bound_90=event_bound,
        scoring_points_per_event=coefficient,
        impact_bound_90=impact,
        supported_fantasy_point_stddev=supported_fantasy_point_stddev,
        allowed_impact_90=allowance,
        reason=(
            "frozen all-population impact bound is within 10% of governed 90% "
            "supported-fantasy-point uncertainty"
            if passed
            else "frozen all-population impact bound exceeds the governed materiality allowance"
        ),
        contract_version=contract_version,
    )
