from datetime import UTC, datetime

from fsffl.forecast.league_scoring import ScoringCoverageStatus, classify_scoring_coverage, derive_league_fantasy_point_forecasts
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueRules, LineupRequirement, Position, Provenance, RosterSlot, ScoringRule

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
PROV = Provenance(source="fsffl:live_equal_weight", retrieved_at=AS_OF, effective_at=AS_OF)


def obs(metric: ForecastMetric, mean: float) -> ForecastObservation:
    return ForecastObservation(
        player_id="wr1",
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=metric,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 3, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=mean, stddev=max(0.1, abs(mean) * 0.05)),
        source="fsffl:live_equal_weight",
        model_version="test",
        as_of=AS_OF,
        provenance=PROV,
    )


def test_common_sleeper_fumble_two_point_and_special_teams_rules_do_not_block_forecast() -> None:
    rules = LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(
            ScoringRule(stat="rec", points=0.5),
            ScoringRule(stat="rec_yd", points=0.1),
            ScoringRule(stat="rec_td", points=6.0),
            ScoringRule(stat="fum_lost", points=-2.0),
            ScoringRule(stat="fum_rec", points=2.0),
            ScoringRule(stat="fum_rec_td", points=6.0),
            ScoringRule(stat="pass_2pt", points=2.0),
            ScoringRule(stat="rec_2pt", points=2.0),
            ScoringRule(stat="rush_2pt", points=2.0),
            ScoringRule(stat="st_ff", points=1.0),
            ScoringRule(stat="st_fum_rec", points=1.0),
            ScoringRule(stat="st_td", points=6.0),
        ),
    )
    coverage = classify_scoring_coverage(rules)
    assert coverage.status == ScoringCoverageStatus.PROVISIONAL
    assert coverage.unsupported_rule_stats == ()
    assert set(coverage.provisional_residual_rule_stats) == {
        "fum_rec", "fum_rec_td", "pass_2pt", "rec_2pt", "rush_2pt", "st_ff", "st_fum_rec", "st_td"
    }
    forecasts = derive_league_fantasy_point_forecasts(
        (
            obs(ForecastMetric.RECEPTIONS, 80.0),
            obs(ForecastMetric.REC_YARDS, 1200.0),
            obs(ForecastMetric.REC_TD, 8.0),
            obs(ForecastMetric.FUMBLES_LOST, 1.0),
        ),
        rules=rules,
    )
    assert len(forecasts) == 1
    assert forecasts[0].distribution.mean > 206.0
    assert "bounded_provisional_residual_v1" in forecasts[0].model_version
