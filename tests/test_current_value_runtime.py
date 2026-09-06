from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.state.models import (
    DraftPick,
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    ProviderRef,
    RosterEntry,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)
from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult, build_current_market_values
from fsffl.value.models import ValueAssetKind


def _state(*, as_of: datetime) -> LeagueState:
    league_id = "sleeper:123"
    provenance = Provenance(
        source="test",
        retrieved_at=as_of,
        effective_at=as_of,
    )
    players = (
        Player(player_id="p1", full_name="Alpha QB", position=Position.QB, provider_refs=(ProviderRef(provider="sleeper", external_id="s1"),)),
        Player(player_id="p2", full_name="Beta RB", position=Position.RB, provider_refs=(ProviderRef(provider="sleeper", external_id="s2"),)),
        Player(player_id="p3", full_name="Gamma WR", position=Position.WR, provider_refs=(ProviderRef(provider="sleeper", external_id="s3"),)),
    )
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Test League",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=2,
                rookie_draft_rounds=3,
                lineup=(
                    LineupRequirement(slot=RosterSlot.QB, count=1),
                    LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
                ),
                scoring=(ScoringRule(stat="rec", points=0.5),),
            ),
            provider_refs=(ProviderRef(provider="sleeper", external_id="123"),),
        ),
        as_of=as_of,
        teams=(
            Team(team_id="t1", league_id=league_id, display_name="One"),
            Team(team_id="t2", league_id=league_id, display_name="Two"),
        ),
        team_states=(
            TeamState(team_id="t1", roster=(RosterEntry(player_id="p1", slot=RosterSlot.QB), RosterEntry(player_id="p2", slot=RosterSlot.RB))),
            TeamState(team_id="t2", roster=(RosterEntry(player_id="p3", slot=RosterSlot.WR),)),
        ),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=as_of,
                status=PlayerStatus.ACTIVE,
                provenance=provenance,
            )
            for player in players
        ),
        draft_picks=(
            DraftPick(
                pick_id="canonical-2027-r1-t1",
                league_id=league_id,
                season=2027,
                round=1,
                original_team_id="t1",
            ),
        ),
        provenance=(provenance,),
    )


def test_current_market_runtime_uses_governed_lineage_and_cardinal_authority(monkeypatch) -> None:
    now = datetime.now(UTC)
    league_state = _state(as_of=now)

    dealer = {
        "players": [
            {"sleeper_id": "s1", "current_value": 9000, "updated_at": now.isoformat()},
            {"sleeper_id": "s2", "current_value": 6000, "updated_at": now.isoformat()},
            {"sleeper_id": "s3", "current_value": 3000, "updated_at": now.isoformat()},
        ]
    }
    calc = [
        {"player": {"sleeperId": "s1"}, "value": 10000},
        {"player": {"sleeperId": "s2"}, "value": 5000},
        {"player": {"sleeperId": "s3"}, "value": 1000},
    ]
    statsguy = {
        "asOf": now.isoformat(),
        "rankings": [
            {"id": "s1", "value": 8740},
            {"id": "s2", "value": 4200},
            {"id": "s3", "value": 1100},
        ],
    }
    statsguy_picks = {
        "valuesAsOf": {"sf_dynasty": now.isoformat()},
        "picks": [
            {"id": "pick:2027:1", "year": 2027, "round": 1, "value": {"sf_dynasty": 3100}},
            {"id": "pick:2027:1:early", "year": 2027, "round": 1, "variant": "early", "value": {"sf_dynasty": 4100}},
        ],
    }

    def fake_download(url: str) -> str:
        if "dynastydealer" in url:
            return json.dumps(dealer)
        if "fantasycalc" in url:
            return json.dumps(calc)
        if url.endswith("/picks"):
            return json.dumps(statsguy_picks)
        if "statsguy" in url:
            return json.dumps(statsguy)
        raise AssertionError(url)

    monkeypatch.setattr("fsffl.value.current_runtime._download_text", fake_download)
    result = build_current_market_values(league_state)

    assert result.league_state_id == league_state.state_id
    assert result.valued_roster_player_count == 3
    assert result.coverage == 1.0
    assert result.cardinal_player_coverage == 1.0
    assert set(result.successful_source_ids) == {
        "dynastydealer_market_values",
        "fantasycalc_market_values",
        "statsguy_market_values",
    }
    assert "dynastyprocess_market_values" in result.failed_sources
    assert "statsguy_pick_values" not in result.failed_sources

    native = {(item.source_id, item.asset_id): item for item in result.native_magnitude_observations}
    assert native[("dynastydealer_market_values", "p1")].value == 9000
    assert native[("fantasycalc_market_values", "p1")].value == 10000
    assert native[("statsguy_market_values", "p1")].value == 8740
    assert native[("dynastydealer_market_values", "p1")].native_scale_id == "dynastydealer-current-value"

    provisional = {item.asset_id: item for item in result.provisional_fsffl_values}
    assert provisional["p1"].score == 9000
    assert provisional["p1"].status == "challenger"

    cardinal = {item.asset_id: item for item in result.fsffl_cardinal_values}
    assert cardinal["p1"].score == 8740
    assert cardinal["p1"].authority_status == "authoritative_market_cardinal"
    assert cardinal["p1"].asset_kind == ValueAssetKind.PLAYER
    assert cardinal["canonical-2027-r1-t1"].score == 3100
    assert cardinal["canonical-2027-r1-t1"].asset_kind == ValueAssetKind.PICK
    assert cardinal["canonical-2027-r1-t1"].slot_certainty == "generic_unknown_slot"

    estimates = {item.asset_id: item for item in result.estimates}
    assert estimates["p1"].distribution.mean == 1.0
    assert estimates["p2"].distribution.mean == 0.5
    assert estimates["p3"].distribution.mean == 0.0
    # All three live providers share one conservative revealed-transaction root,
    # so correlated feeds become one authoritative vote rather than triple weight.
    assert estimates["p1"].distribution.stddev == 0.0


def test_runtime_rejects_value_evidence_for_stale_state() -> None:
    now = datetime.now(UTC)
    state = _state(as_of=now)
    newer = _state(as_of=now + timedelta(seconds=1))
    store = PrivateBetaRuntimeStore()
    store.set_league_state("u1", newer)

    stale = CurrentMarketValueRuntimeResult(
        league_state_id=state.state_id,
        estimates=(),
        successful_source_ids=(),
        failed_sources=(),
        errors_by_source_id={},
        roster_player_count=3,
        valued_roster_player_count=0,
        market_context_id="dynasty:2t:sf:0.5ppr",
    )
    with pytest.raises(ValueError, match="must match current LeagueState"):
        store.set_value_evidence("u1", stale)
