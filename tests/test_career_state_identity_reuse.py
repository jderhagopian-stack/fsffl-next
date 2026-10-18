"""Compute exact immutable State identity once per bounded roster operation."""
from datetime import UTC, datetime
from types import SimpleNamespace

from fsffl.product.foundation4_shadow_routes import _career_position_depth_rows
from fsffl.product.foundation4_dynamic_candidate_runtime import _candidate_rows, _roster_inputs
from fsffl.state.models import Position, RosterSlot


class CountedState:
    def __init__(self, count=255, identity='exact-state'):
        self.identity, self.identity_reads = identity, 0
        self.as_of = datetime(2026,10,18,tzinfo=UTC)
        self.players = tuple(SimpleNamespace(player_id=f'player:{i}', position=Position.WR)
                             for i in range(count))
        self.player_states = tuple(SimpleNamespace(player_id=p.player_id,age_years=24.) for p in self.players)
        self.team_states = (SimpleNamespace(team_id='team',roster=tuple(
            SimpleNamespace(player_id=p.player_id,slot=RosterSlot.BENCH) for p in self.players)),)

    @property
    def state_id(self):
        self.identity_reads += 1
        return self.identity


def test_position_depth_hashes_full_state_once_and_preserves_all_outcomes():
    state = CountedState()
    career = SimpleNamespace(estimates=tuple(SimpleNamespace(player_id=p.player_id)
                                             for p in state.players),player_coverage_failures={})
    rows = _career_position_depth_rows(state,career)
    assert state.identity_reads == 1
    assert len(rows) == 255
    assert {r['state_hash'] for r in rows} == {'exact-state'}
    assert {r['career_coverage_status'] for r in rows} == {'career_authority_available'}
    assert {r['player_id'] for r in rows} == {p.player_id for p in state.players}
    # Another invocation/State must compute its own exact identity, not use a
    # process/user cache or copy the previous publication's hash.
    replacement = CountedState(identity='new-state')
    replaced = _career_position_depth_rows(replacement,career)
    assert replacement.identity_reads == 1
    assert {r['state_hash'] for r in replaced} == {'new-state'}
    assert {r['state_hash'] for r in rows} == {'exact-state'}


def test_materializer_full_roster_hashes_once_without_losing_provenance():
    state = CountedState()
    rows = _roster_inputs(SimpleNamespace(league_state=state))
    assert state.identity_reads == 1
    assert len(rows) == 255
    assert all(r['state_hash']=='exact-state' and r['state_as_of']==state.as_of.isoformat()
               and r['age']==24. and r['roster_slot']=='BENCH' for r in rows)


def test_candidate_batch_hashes_once_and_keeps_player_specific_failures():
    state = CountedState()
    ids = tuple(p.player_id for p in state.players[:30]) + ('missing-player',)
    source = SimpleNamespace(historical_gsis_id=None,experience=0.,connected_league_y1_points=1.8)
    live = SimpleNamespace(evaluation_as_of=state.as_of,
        candidate_source_rows={pid:source for pid in ids},
        future=SimpleNamespace(contract=SimpleNamespace(
            forecast_model_version='accepted-fixture',scoring_coordinate='connected_league_fantasy_points')))
    forecasts = {(pid,year):SimpleNamespace(central_expectation=10.+year)
                 for pid in ids for year in (2,3)}
    rows, failures = _candidate_rows(SimpleNamespace(league_state=state),live,ids,forecasts)
    assert state.identity_reads == 1
    assert len(rows) == 30
    assert set(failures) == {'missing-player'}
    assert all(r['state_hash']=='exact-state' and r['evaluation_as_of']==state.as_of.isoformat()
               and r['league_y1_points']==1.8 and r['y2_player_league_expected_points']==12.
               for r in rows)
