from datetime import UTC, datetime

from fsffl.team_utility.draft_metric_simulation import (
    DraftMetricSimulationInput,
    TeamDraftMetricDistribution,
    simulate_draft_metric,
)


def test_metric_simulation_preserves_metric_identity_and_team_coverage():
    request = DraftMetricSimulationInput(
        league_id="league-generic",
        draft_season=2027,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        metric_id="max_pf",
        distributions=(
            TeamDraftMetricDistribution(
                team_id="a",
                mean_value=100,
                stddev_value=0,
                model_version="max-pf-input-v1",
            ),
            TeamDraftMetricDistribution(
                team_id="b",
                mean_value=120,
                stddev_value=0,
                model_version="max-pf-input-v1",
            ),
        ),
        simulation_count=4,
        seed=1,
        model_version="draft-metric-sim-v1",
        provenance="point-in-time max-pf distribution evidence",
    )

    result = simulate_draft_metric(request)

    assert result.metric_id == "max_pf"
    assert result.as_of == request.as_of
    assert len(result.scenarios) == 4
    assert sum(row.probability for row in result.scenarios) == 1.0
    assert all({m.team_id for m in row.metrics} == {"a", "b"} for row in result.scenarios)
    assert all({m.value for m in row.metrics} == {100, 120} for row in result.scenarios)
    assert "max-pf-input-v1" in result.model_version


def test_metric_simulation_does_not_rank_or_infer_draft_order():
    request = DraftMetricSimulationInput(
        league_id="league-generic",
        draft_season=2027,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        metric_id="custom_metric",
        distributions=(
            TeamDraftMetricDistribution(team_id="a", mean_value=10, stddev_value=0, model_version="input-v1"),
            TeamDraftMetricDistribution(team_id="b", mean_value=20, stddev_value=0, model_version="input-v1"),
        ),
        simulation_count=1,
        model_version="draft-metric-sim-v1",
        provenance="generic metric evidence",
    )

    result = simulate_draft_metric(request)
    scenario = result.scenarios[0]

    # Simulation returns metric outcomes only. Draft-slot ordering is a separate
    # league-policy operation in the ranked-metric producer.
    assert [(m.team_id, m.value) for m in scenario.metrics] == [("a", 10), ("b", 20)]
