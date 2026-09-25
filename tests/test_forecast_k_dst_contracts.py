from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.forecast.k_dst_scoring import (
    ForecastSubjectFamily,
    GameRuleProbabilityDistribution,
    RuleEvidenceStatus,
    RuleProbability,
    SourceRuleEvidence,
    TeamUnitDistributionalEvidence,
    derive_dst_fantasy_point_forecasts,
    derive_kicker_fantasy_point_forecasts,
    evaluate_rule_evidence_coverage,
)
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
    NflTeamUnitForecastSubject,
    PlayerForecastSubject,
    TeamUnitForecastObservation,
    forecast_subject_for_roster_asset,
)
from fsffl.forecast.season_uncertainty import apply_empirical_season_fantasy_point_uncertainty
from fsffl.state.models import (
    LeagueRules,
    LineupRequirement,
    Position,
    Provenance,
    RosterSlot,
    ScoringRule,
)


AS_OF = datetime(2026, 9, 1, tzinfo=UTC)
END = datetime(2027, 1, 10, tzinfo=UTC)
PROVENANCE = Provenance(source="fixture", retrieved_at=AS_OF, effective_at=AS_OF)


def _rules(
    *,
    k: bool = False,
    dst: bool = False,
    scoring: tuple[ScoringRule, ...],
) -> LeagueRules:
    lineup = [LineupRequirement(slot=RosterSlot.QB, count=1)]
    if k:
        lineup.append(LineupRequirement(slot=RosterSlot.K, count=1))
    if dst:
        lineup.append(LineupRequirement(slot=RosterSlot.DST, count=1))
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=tuple(lineup),
        scoring=scoring,
    )


def _k_obs(metric: ForecastMetric, mean: float, stddev: float = 0.0) -> ForecastObservation:
    return ForecastObservation(
        player_id="sleeper:player:k1",
        position=Position.K,
        horizon=ForecastHorizon.SEASON,
        metric=metric,
        period_start=AS_OF,
        period_end=END,
        distribution=ForecastDistribution(mean=mean, stddev=stddev),
        source="synthetic-ensemble",
        model_version="fixture-v1",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )


def _dst_obs(
    subject: NflTeamUnitForecastSubject,
    metric: ForecastMetric,
    mean: float,
    stddev: float = 0.0,
) -> TeamUnitForecastObservation:
    return TeamUnitForecastObservation(
        subject=subject,
        horizon=ForecastHorizon.SEASON,
        metric=metric,
        period_start=AS_OF,
        period_end=END,
        distribution=ForecastDistribution(mean=mean, stddev=stddev),
        source="synthetic-ensemble",
        model_version="fixture-v1",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )


def test_dst_is_team_season_subject_and_aliases_are_deterministic() -> None:
    with pytest.raises(ValueError, match="D/ST Forecast subjects"):
        PlayerForecastSubject(player_id="sleeper:player:JAC", position=Position.DST)
    with pytest.raises(ValueError, match="TeamUnitForecastObservation"):
        ForecastObservation(
            player_id="sleeper:player:JAC",
            position=Position.DST,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.DST_SACK,
            period_start=AS_OF,
            period_end=END,
            distribution=ForecastDistribution(mean=40, stddev=4),
            source="invalid-player-shaped-dst",
            model_version="fixture-v1",
            as_of=AS_OF,
            provenance=PROVENANCE,
        )

    subject = forecast_subject_for_roster_asset(
        player_id="sleeper:player:JAC",
        position=Position.DST,
        season=2026,
        nfl_team="JAC",
    )
    assert isinstance(subject, NflTeamUnitForecastSubject)
    assert subject.nfl_team == "JAX"
    assert subject.roster_asset_key == "nfl-team-unit:2026:JAX:DST"


def test_k_50_plus_does_not_satisfy_distinct_50_59_and_60_plus_rules() -> None:
    rules = _rules(
        k=True,
        scoring=(
            ScoringRule(stat="fgm_50_59", points=5),
            ScoringRule(stat="fgm_60p", points=6),
        ),
    )
    sources = (
        SourceRuleEvidence(
            source_id="a",
            independence_group="a",
            metrics=frozenset({ForecastMetric.FG_MADE_50_PLUS}),
        ),
        SourceRuleEvidence(
            source_id="b",
            independence_group="b",
            metrics=frozenset({ForecastMetric.FG_MADE_50_PLUS}),
        ),
    )

    coverage = evaluate_rule_evidence_coverage(
        rules,
        subject_family=ForecastSubjectFamily.KICKER,
        sources=sources,
    )

    assert {item.rule_stat for item in coverage} == {"fgm_50_59", "fgm_60p"}
    assert all(item.status == RuleEvidenceStatus.UNSUPPORTED for item in coverage)


def test_aggregate_overlap_does_not_masquerade_as_two_independent_sources() -> None:
    rules = _rules(
        k=True,
        scoring=(ScoringRule(stat="xpm", points=1),),
    )
    sources = (
        SourceRuleEvidence(
            source_id="provider-a",
            independence_group="shared-corpus",
            metrics=frozenset({ForecastMetric.XP_MADE}),
        ),
        SourceRuleEvidence(
            source_id="aggregate-a",
            independence_group="shared-corpus",
            metrics=frozenset({ForecastMetric.XP_MADE}),
        ),
    )

    coverage = evaluate_rule_evidence_coverage(
        rules,
        subject_family=ForecastSubjectFamily.KICKER,
        sources=sources,
    )

    assert coverage[0].status == RuleEvidenceStatus.UNSUPPORTED


def test_kicker_exact_scoring_matches_hand_calculation_but_uncertainty_stays_gated() -> None:
    rules = _rules(
        k=True,
        scoring=(
            ScoringRule(stat="fgm_0_19", points=3),
            ScoringRule(stat="fgm_20_29", points=3),
            ScoringRule(stat="fgm_30_39", points=3),
            ScoringRule(stat="fgm_40_49", points=4),
            ScoringRule(stat="fgm_50_59", points=5),
            ScoringRule(stat="fgm_60p", points=6),
            ScoringRule(stat="fgmiss", points=-1),
            ScoringRule(stat="xpm", points=1),
            ScoringRule(stat="xpmiss", points=-1),
        ),
    )
    observations = (
        _k_obs(ForecastMetric.FG_MADE_0_19, 1),
        _k_obs(ForecastMetric.FG_MADE_20_29, 2),
        _k_obs(ForecastMetric.FG_MADE_30_39, 3),
        _k_obs(ForecastMetric.FG_MADE_40_49, 4),
        _k_obs(ForecastMetric.FG_MADE_50_59, 5),
        _k_obs(ForecastMetric.FG_MADE_60_PLUS, 1),
        _k_obs(ForecastMetric.FG_MISS, 2),
        _k_obs(ForecastMetric.XP_MADE, 20),
        _k_obs(ForecastMetric.XP_MISS, 1),
    )

    scored = derive_kicker_fantasy_point_forecasts(observations, rules=rules)
    assert len(scored) == 1
    assert scored[0].distribution.mean == pytest.approx(82.0)

    with pytest.raises(ValueError, match="no promoted season fantasy-point uncertainty calibration for K"):
        apply_empirical_season_fantasy_point_uncertainty(scored)


def test_dst_linear_scoring_uses_team_unit_observations() -> None:
    subject = NflTeamUnitForecastSubject(season=2026, nfl_team="DEN")
    rules = _rules(
        dst=True,
        scoring=(
            ScoringRule(stat="sack", points=1),
            ScoringRule(stat="int", points=2),
            ScoringRule(stat="fum_rec", points=2),
            ScoringRule(stat="ff", points=1),
            ScoringRule(stat="safe", points=2),
            ScoringRule(stat="blk_kick", points=2),
            ScoringRule(stat="def_td", points=6),
        ),
    )
    observations = (
        _dst_obs(subject, ForecastMetric.DST_SACK, 40),
        _dst_obs(subject, ForecastMetric.DST_INTERCEPTION, 15),
        _dst_obs(subject, ForecastMetric.DST_FUMBLE_RECOVERY, 10),
        _dst_obs(subject, ForecastMetric.DST_FORCED_FUMBLE, 8),
        _dst_obs(subject, ForecastMetric.DST_SAFETY, 1),
        _dst_obs(subject, ForecastMetric.DST_BLOCKED_KICK, 2),
        _dst_obs(subject, ForecastMetric.DST_DEFENSIVE_TD, 4),
    )

    scored = derive_dst_fantasy_point_forecasts(observations, rules=rules)
    assert len(scored) == 1
    assert scored[0].subject == subject
    assert scored[0].distribution.mean == pytest.approx(128.0)


def test_dst_bucket_scoring_requires_per_game_distributional_evidence() -> None:
    subject = NflTeamUnitForecastSubject(season=2026, nfl_team="DEN")
    rules = _rules(
        dst=True,
        scoring=(
            ScoringRule(stat="pts_allow_0", points=10),
            ScoringRule(stat="pts_allow_1_6", points=7),
            ScoringRule(stat="pts_allow_7_13", points=4),
        ),
    )

    aggregate_only = (
        SourceRuleEvidence(source_id="a", independence_group="a"),
        SourceRuleEvidence(source_id="b", independence_group="b"),
    )
    aggregate_coverage = evaluate_rule_evidence_coverage(
        rules,
        subject_family=ForecastSubjectFamily.DST,
        sources=aggregate_only,
    )
    assert all(item.status == RuleEvidenceStatus.UNSUPPORTED for item in aggregate_coverage)

    evidence = TeamUnitDistributionalEvidence(
        subject=subject,
        family="points_allowed",
        horizon=ForecastHorizon.SEASON,
        period_start=AS_OF,
        period_end=END,
        games=(
            GameRuleProbabilityDistribution(
                game_key="g1",
                probabilities=(
                    RuleProbability(rule_stat="pts_allow_0", probability=0.2),
                    RuleProbability(rule_stat="pts_allow_1_6", probability=0.3),
                    RuleProbability(rule_stat="pts_allow_7_13", probability=0.5),
                ),
            ),
            GameRuleProbabilityDistribution(
                game_key="g2",
                probabilities=(
                    RuleProbability(rule_stat="pts_allow_0", probability=0.1),
                    RuleProbability(rule_stat="pts_allow_1_6", probability=0.4),
                    RuleProbability(rule_stat="pts_allow_7_13", probability=0.5),
                ),
            ),
        ),
        source="synthetic-distribution",
        model_version="fixture-v1",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )

    scored = derive_dst_fantasy_point_forecasts(
        (),
        distributional_evidence=(evidence,),
        rules=rules,
    )
    assert len(scored) == 1
    assert scored[0].distribution.mean == pytest.approx(11.9)


def test_team_and_player_special_teams_rule_names_do_not_cross_contaminate() -> None:
    subject = NflTeamUnitForecastSubject(season=2026, nfl_team="DEN")
    rules = _rules(
        dst=True,
        scoring=(
            ScoringRule(stat="def_st_td", points=6),
            ScoringRule(stat="st_td", points=6),
        ),
    )

    scored = derive_dst_fantasy_point_forecasts(
        (_dst_obs(subject, ForecastMetric.DST_TEAM_ST_TD, 1),),
        rules=rules,
    )
    assert len(scored) == 1
    assert scored[0].distribution.mean == pytest.approx(6.0)


def test_fixture_a_no_k_or_dst_leaves_offense_path_and_family_coverage_unchanged() -> None:
    rules = _rules(scoring=(ScoringRule(stat="pass_yd", points=0.04),))
    assert evaluate_rule_evidence_coverage(
        rules,
        subject_family=ForecastSubjectFamily.KICKER,
        sources=(),
    ) == ()
    assert evaluate_rule_evidence_coverage(
        rules,
        subject_family=ForecastSubjectFamily.DST,
        sources=(),
    ) == ()


def test_fixture_g_k_and_dst_can_be_scored_without_cross_family_double_counting() -> None:
    rules = LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.K, count=1),
            LineupRequirement(slot=RosterSlot.DST, count=1),
        ),
        scoring=(
            ScoringRule(stat="xpm", points=1),
            ScoringRule(stat="def_st_td", points=6),
            ScoringRule(stat="st_td", points=6),
        ),
    )
    kicker = derive_kicker_fantasy_point_forecasts(
        (_k_obs(ForecastMetric.XP_MADE, 20),),
        rules=rules,
    )
    subject = NflTeamUnitForecastSubject(season=2026, nfl_team="DEN")
    dst = derive_dst_fantasy_point_forecasts(
        (_dst_obs(subject, ForecastMetric.DST_TEAM_ST_TD, 2),),
        rules=rules,
    )

    assert kicker[0].distribution.mean == pytest.approx(20)
    assert dst[0].distribution.mean == pytest.approx(12)
    # Player special-teams rule st_td is not a D/ST coordinate and therefore
    # cannot duplicate the team-unit def_st_td credit.
    assert dst[0].distribution.mean != pytest.approx(24)
