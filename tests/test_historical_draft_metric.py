from datetime import UTC, datetime

from fsffl.runtime.historical_draft_metric import build_observed_draft_metric_scenarios
from fsffl.state.draft_metric import HistoricalTeamDraftMetric, resolve_historical_draft_metrics
from fsffl.state.models import LeagueRules, Provenance


RULES = LeagueRules(team_count=2, roster_size=20, rookie_draft_rounds=3, lineup=(), scoring=())


def _metric(team_id: str, value: float, available_at: datetime, version: str = "metric-v1"):
    return HistoricalTeamDraftMetric(
        league_id="league-generic",
        draft_season=2027,
        team_id=team_id,
        metric_id="max_pf",
        value=value,
        effective_at=available_at,
        available_at=available_at,
        model_version=version,
        provenance=Provenance(
            source="historical-provider-snapshot",
            retrieved_at=available_at,
            effective_at=available_at,
        ),
    )


def test_observed_metric_resolution_never_uses_future_evidence():
    as_of = datetime(2026, 9, 1, tzinfo=UTC)
    observations = (
        _metric("a", 100, datetime(2026, 8, 1, tzinfo=UTC)),
        _metric("a", 120, datetime(2026, 10, 1, tzinfo=UTC), version="metric-v2"),
    )
    resolved = resolve_historical_draft_metrics(
        observations,
        league_id="league-generic",
        draft_season=2027,
        metric_id="max_pf",
        as_of=as_of,
    )
    assert len(resolved) == 1
    assert resolved[0].value == 100


def test_observed_metric_builder_requires_complete_league_evidence():
    as_of = datetime(2026, 9, 1, tzinfo=UTC)
    assert build_observed_draft_metric_scenarios(
        observations=(_metric("a", 100, datetime(2026, 8, 1, tzinfo=UTC)),),
        league_id="league-generic",
        draft_season=2027,
        metric_id="max_pf",
        as_of=as_of,
        league_rules=RULES,
    ) is None


def test_complete_observed_metric_becomes_deterministic_scenario():
    as_of = datetime(2026, 9, 1, tzinfo=UTC)
    result = build_observed_draft_metric_scenarios(
        observations=(
            _metric("a", 100, datetime(2026, 8, 1, tzinfo=UTC)),
            _metric("b", 120, datetime(2026, 8, 1, tzinfo=UTC)),
        ),
        league_id="league-generic",
        draft_season=2027,
        metric_id="max_pf",
        as_of=as_of,
        league_rules=RULES,
    )
    assert result is not None
    assert len(result.scenarios) == 1
    assert result.scenarios[0].probability == 1.0
    assert [(row.team_id, row.value) for row in result.scenarios[0].metrics] == [("a", 100), ("b", 120)]
