from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.current_runtime import (
    LiveForecastRuntimeResult,
    NamedCurrentProjectionFetcher,
    build_current_live_forecasts,
)
from fsffl.forecast.live_ensemble import LiveEnsembleCoverage
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.preseason_baseline import (
    PRESEASON_AUTHORITY_RUNTIME_VERSION,
    baseline_from_runtime,
)
from fsffl.persistence.runtime_cache import preseason_forecast_baseline_artifact
from fsffl.product.forecast_resilience import make_resilient_forecast_loader
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.providers.current_projection_rows import (
    CurrentProjectionRow,
    CurrentProjectionSnapshot,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    ScoringRule,
    Team,
    TeamState,
)


BAD_EFFECTIVE_AT = datetime(2026, 9, 20, 13, 48, 44, tzinfo=UTC)
NOW = datetime(2026, 9, 20, 20, 51, 10, tzinfo=UTC)
BASELINE_AS_OF = datetime(2026, 9, 10, 21, 36, 41, tzinfo=UTC)


def _state() -> LeagueState:
    provenance = Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-v1",
    )
    return LeagueState(
        league=League(
            league_id="league-1",
            name="Fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(
                    ScoringRule(stat="pass_yd", points=0.04),
                    ScoringRule(stat="pass_td", points=4.0),
                    ScoringRule(stat="pass_int", points=-2.0),
                    ScoringRule(stat="rush_yd", points=0.1),
                    ScoringRule(stat="rush_td", points=6.0),
                ),
            ),
        ),
        as_of=NOW,
        teams=(
            Team(team_id="a", league_id="league-1", display_name="A"),
            Team(team_id="b", league_id="league-1", display_name="B"),
        ),
        team_states=(
            TeamState(team_id="a", roster=()),
            TeamState(team_id="b", roster=()),
        ),
        players=(
            Player(
                player_id="josh-allen",
                full_name="Josh Allen",
                position=Position.QB,
                nfl_team="BUF",
            ),
        ),
        player_states=(
            PlayerState(
                player_id="josh-allen",
                as_of=NOW,
                nfl_team="BUF",
                provenance=provenance,
            ),
        ),
    )


def _razzball_snapshot(
    *,
    healthy_revision: bool,
    timestamp_shift: timedelta = timedelta(0),
    reverse_rows: bool = False,
    extra_rows: int = 0,
) -> CurrentProjectionSnapshot:
    def row(
        player_name: str,
        position: Position,
        nfl_team: str,
        **stats: float,
    ) -> CurrentProjectionRow:
        return CurrentProjectionRow(
            provider="razzball",
            external_id=f"{position.value}:{nfl_team}:{player_name.lower().replace(' ', '')}",
            player_name=player_name,
            position=position,
            nfl_team=nfl_team,
            stats=stats,
        )

    rows = [
        row(
            "Josh Allen",
            Position.QB,
            "BUF",
            pass_yd=4200.0 if healthy_revision else 7682.0,
            pass_td=31.0 if healthy_revision else 47.9,
            pass_int=10.0 if healthy_revision else 22.8,
            rush_yd=600.0 if healthy_revision else 1134.0,
            rush_td=9.0 if healthy_revision else 21.9,
            rec=0.0,
            rec_yd=0.0,
            rec_td=0.0,
        ),
        row(
            "Dak Prescott", Position.QB, "DAL",
            pass_yd=7934.0, pass_td=49.3, pass_int=16.2,
            rush_yd=459.0, rush_td=6.0, rec=0.0, rec_yd=0.0, rec_td=0.0,
        ),
        row(
            "Deshaun Watson", Position.QB, "CLE",
            pass_yd=7314.0, pass_td=41.5, pass_int=23.6,
            rush_yd=465.0, rush_td=2.4, rec=0.0, rec_yd=0.0, rec_td=0.0,
        ),
        row(
            "Jahmyr Gibbs", Position.RB, "DET",
            pass_yd=0.0, pass_td=0.0, pass_int=0.0,
            rush_yd=2665.0, rush_td=22.7, rec=119.0, rec_yd=991.0, rec_td=4.7,
        ),
        row(
            "Tony Pollard", Position.RB, "TEN",
            pass_yd=0.0, pass_td=0.0, pass_int=0.0,
            rush_yd=2234.0, rush_td=10.0, rec=51.0, rec_yd=347.0, rec_td=1.0,
        ),
        row(
            "Tyjae Spears", Position.RB, "TEN",
            pass_yd=0.0, pass_td=0.0, pass_int=0.0,
            rush_yd=746.0, rush_td=8.0, rec=67.0, rec_yd=544.0, rec_td=3.0,
        ),
        row(
            "Puka Nacua", Position.WR, "LAR",
            pass_yd=0.0, pass_td=0.0, pass_int=0.0,
            rush_yd=114.0, rush_td=0.9, rec=223.0, rec_yd=2926.0, rec_td=17.0,
        ),
        row(
            "CeeDee Lamb", Position.WR, "DAL",
            pass_yd=0.0, pass_td=0.0, pass_int=0.0,
            rush_yd=22.0, rush_td=0.2, rec=171.0, rec_yd=2276.0, rec_td=12.0,
        ),
        row(
            "Matthew Golden", Position.WR, "GB",
            pass_yd=0.0, pass_td=0.0, pass_int=0.0,
            rush_yd=173.0, rush_td=1.3, rec=111.0, rec_yd=1427.0, rec_td=6.5,
        ),
        row(
            "Brock Bowers", Position.TE, "LV",
            pass_yd=0.0, pass_td=0.0, pass_int=0.0,
            rush_yd=15.0, rush_td=0.1, rec=124.0, rec_yd=1279.0, rec_td=8.5,
        ),
        row(
            "Kyle Pitts", Position.TE, "ATL",
            pass_yd=0.0, pass_td=0.0, pass_int=0.0,
            rush_yd=0.0, rush_td=0.0, rec=138.0, rec_yd=1366.0, rec_td=6.5,
        ),
        row(
            "Dallas Goedert", Position.TE, "PHI",
            pass_yd=0.0, pass_td=0.0, pass_int=0.0,
            rush_yd=0.0, rush_td=0.0, rec=122.0, rec_yd=1236.0, rec_td=12.0,
        ),
    ]
    rows.extend(
        row(
            f"Filler {index}",
            Position.QB,
            "FA",
            pass_yd=1.0,
        )
        for index in range(550 + extra_rows)
    )
    if reverse_rows:
        rows.reverse()
    return CurrentProjectionSnapshot(
        provider="razzball",
        captured_at=NOW + timestamp_shift,
        effective_at=BAD_EFFECTIVE_AT + timestamp_shift,
        rows=tuple(rows),
        source_version="razzball-season-projections-html-v3:horizon-isolated",
        usage_class="beta-personal-research-requires-commercial-review",
    )

def _fftoday_snapshot() -> CurrentProjectionSnapshot:
    return CurrentProjectionSnapshot(
        provider="fftoday",
        captured_at=NOW,
        effective_at=NOW - timedelta(hours=1),
        rows=(
            CurrentProjectionRow(
                provider="fftoday",
                external_id="fftoday-josh",
                player_name="Josh Allen",
                position=Position.QB,
                nfl_team="BUF",
                stats={
                    "pass_yd": 4000.0,
                    "pass_td": 30.0,
                    "pass_int": 10.0,
                    "rush_yd": 550.0,
                    "rush_td": 8.0,
                },
            ),
        ),
        source_version="fftoday-fixture-v1",
        usage_class="fixture",
    )


def _baseline_runtime(state: LeagueState) -> LiveForecastRuntimeResult:
    provenance = Provenance(
        source="fsffl:live_equal_weight[fftoday,razzball]",
        retrieved_at=BASELINE_AS_OF,
        effective_at=BASELINE_AS_OF,
        source_version="next2-live-equal-weight-v1",
    )
    raw = tuple(
        ForecastObservation(
            player_id="josh-allen",
            position=Position.QB,
            horizon=ForecastHorizon.SEASON,
            metric=metric,
            period_start=datetime(2026, 9, 1, tzinfo=UTC),
            period_end=datetime(2027, 3, 1, tzinfo=UTC),
            distribution=ForecastDistribution(mean=mean, stddev=0.0),
            source="fsffl:live_equal_weight",
            model_version="next2-live-equal-weight-v1",
            as_of=BASELINE_AS_OF,
            provenance=provenance,
        )
        for metric, mean in (
            (ForecastMetric.PASS_YARDS, 4200.0),
            (ForecastMetric.PASS_TD, 31.0),
            (ForecastMetric.INTERCEPTIONS, 10.0),
            (ForecastMetric.RUSH_YARDS, 600.0),
            (ForecastMetric.RUSH_TD, 9.0),
        )
    )
    coverage = LiveEnsembleCoverage(
        independent_source_ids=("fftoday", "razzball"),
        excluded_aggregate_source_ids=(),
        active_source_ids=("fftoday", "razzball"),
        observation_count=len(raw) * 2,
        minimum_independent_sources=2,
    )
    return LiveForecastRuntimeResult(
        raw_ensemble=raw,
        fantasy_point_forecasts=(),
        coverage=coverage,
        successful_source_ids=("fftoday", "razzball"),
        failed_sources=(),
        evaluation_as_of=BASELINE_AS_OF,
    )


class _Store:
    def __init__(self, record):
        self.record = record
        self.puts = []

    def get_latest_reusable_artifact(self, **_kwargs):
        return self.record

    def put_artifact(self, record):
        self.puts.append(record)
        self.record = record


def _evidence_from_live(
    state: LeagueState,
    *,
    healthy_revision: bool,
    timestamp_shift: timedelta = timedelta(0),
    reverse_rows: bool = False,
    extra_rows: int = 0,
) -> LiveForecastEvidence:
    result = build_current_live_forecasts(
        state,
        fetchers=(
            NamedCurrentProjectionFetcher(
                source_id="razzball",
                fetch=lambda _season: _razzball_snapshot(
                    healthy_revision=healthy_revision,
                    timestamp_shift=timestamp_shift,
                    reverse_rows=reverse_rows,
                    extra_rows=extra_rows,
                ),
            ),
            NamedCurrentProjectionFetcher(
                source_id="fftoday",
                fetch=lambda _season: _fftoday_snapshot(),
            ),
        ),
        clock=lambda: NOW,
    )
    return LiveForecastEvidence(
        raw_forecasts=result.raw_ensemble,
        league_scored_forecasts=result.fantasy_point_forecasts,
        successful_source_ids=result.successful_source_ids,
        failed_sources=result.failed_sources,
        uncertainty_ready=True,
        runtime_result=result,
        evidence_basis="live_full_season",
    )


def test_known_bad_razzball_revision_cannot_enter_live_ensemble() -> None:
    with pytest.raises(
        ValueError,
        match="authoritative live ensemble requires at least 2 independent sources",
    ) as excinfo:
        _evidence_from_live(_state(), healthy_revision=False)

    message = str(excinfo.value)
    assert "razzball-full-season-upstream-inflation-20260920" in message
    assert "successful=['fftoday']" in message


def test_same_malformed_content_with_new_timestamps_is_still_quarantined() -> None:
    with pytest.raises(ValueError) as excinfo:
        _evidence_from_live(
            _state(),
            healthy_revision=False,
            timestamp_shift=timedelta(minutes=5),
        )

    assert "razzball-full-season-upstream-inflation-20260920" in str(excinfo.value)


def test_same_malformed_content_with_reordered_rows_is_still_quarantined() -> None:
    with pytest.raises(ValueError) as excinfo:
        _evidence_from_live(
            _state(),
            healthy_revision=False,
            reverse_rows=True,
        )

    assert "razzball-full-season-upstream-inflation-20260920" in str(excinfo.value)


def test_same_malformed_content_with_changed_row_count_is_still_quarantined() -> None:
    with pytest.raises(ValueError) as excinfo:
        _evidence_from_live(
            _state(),
            healthy_revision=False,
            extra_rows=3,
        )

    assert "razzball-full-season-upstream-inflation-20260920" in str(excinfo.value)


def test_malformed_razzball_uses_preserved_preseason_authority_without_rewrite() -> None:
    state = _state()
    baseline = baseline_from_runtime(
        state,
        _baseline_runtime(state),
        source_artifact_id="94",
    )
    record = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026",
        baseline=baseline,
    )
    store = _Store(record)

    loader = make_resilient_forecast_loader(
        store,
        live_loader=lambda current_state: _evidence_from_live(
            current_state,
            healthy_revision=False,
        ),
    )
    evidence = loader(state)

    season = [
        item
        for item in evidence.league_scored_forecasts
        if item.horizon == ForecastHorizon.SEASON
        and item.metric == ForecastMetric.FANTASY_POINTS
    ]
    assert len(season) == 1
    assert evidence.evidence_basis == "preseason_baseline"
    assert evidence.runtime_result.model_version == PRESEASON_AUTHORITY_RUNTIME_VERSION
    assert evidence.successful_source_ids == ("fftoday", "razzball")
    assert season[0].source == "fsffl:preseason_baseline_league_scored"
    assert season[0].distribution.mean == pytest.approx(386.0)
    assert season[0].distribution.mean < 500.0
    assert "razzball-full-season-upstream-inflation-20260920" in evidence.failed_sources[0]
    assert store.puts == []
    assert store.record is record


def test_valid_new_razzball_revision_continues_through_governed_live_path() -> None:
    state = _state()
    baseline = baseline_from_runtime(
        state,
        _baseline_runtime(state),
        source_artifact_id="94",
    )
    record = preseason_forecast_baseline_artifact(
        league_season_scope_id="league-1:2026",
        baseline=baseline,
    )
    store = _Store(record)

    evidence = make_resilient_forecast_loader(
        store,
        live_loader=lambda current_state: _evidence_from_live(
            current_state,
            healthy_revision=True,
        ),
    )(state)

    assert evidence.evidence_basis == "live_full_season"
    assert evidence.successful_source_ids == ("fftoday", "razzball")
    assert evidence.failed_sources == ()
    assert store.puts == []
    assert evidence.league_scored_forecasts[0].source == "fsffl:live_league_scored"
