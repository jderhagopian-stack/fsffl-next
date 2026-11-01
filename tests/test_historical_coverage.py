"""League-agnostic historical evidence inventory, no live providers or data."""
from datetime import UTC, datetime, timedelta, timezone

import pytest

from fsffl.state.historical_coverage import (
    HistoricalEvidenceKind as Kind,
    HistoricalEvidenceReceipt,
    HistoricalSeasonIdentity,
    inventory_historical_cutoff,
)
from fsffl.state.models import (
    League, LeagueRules, LeagueState, LineupRequirement, RosterSlot,
    ScoringRule, Team, TeamState,
)


def moment(season: int, month: int = 9, day: int = 1) -> datetime:
    return datetime(season, month, day, 12, tzinfo=UTC)


def state(*, league_id: str, season: int, count: int, time: datetime,
          slots: tuple[tuple[RosterSlot, int], ...], roster: int,
          scoring: tuple[tuple[str, float], ...]) -> LeagueState:
    return LeagueState(
        league=League(league_id=league_id, name="Independent test league", season=season,
                      rules=LeagueRules(team_count=count, roster_size=roster,
                                        taxi_size=3, ir_size=2, rookie_draft_rounds=5,
                                        lineup=tuple(LineupRequirement(slot=s, count=n) for s,n in slots),
                                        scoring=tuple(ScoringRule(stat=k, points=v) for k,v in scoring))),
        as_of=time,
        teams=tuple(Team(team_id=f"t-{n}", league_id=league_id, display_name=f"T{n}") for n in range(count)),
        team_states=tuple(TeamState(team_id=f"t-{n}", roster=()) for n in range(count)),
        players=(), player_states=(),
    )


def receipt(season, kind, evidence_id, *, effective=None, available=None, basis="provider_timestamp"):
    return HistoricalEvidenceReceipt(season=season,kind=kind,evidence_id=evidence_id,
                                     effective_at=effective or moment(season.season),
                                     available_at=available,availability_basis=basis if available else None,
                                     source="fixture-provider",source_version="snapshot-1")


@pytest.mark.parametrize("count,slots",[
    (2, ((RosterSlot.QB,1),)),
    (8, ((RosterSlot.QB,1),(RosterSlot.RB,2),(RosterSlot.WR,2),(RosterSlot.K,1),(RosterSlot.DST,1))),
    (12, ((RosterSlot.QB,1),(RosterSlot.WR,3),(RosterSlot.SUPERFLEX,1))),
    (16, ((RosterSlot.QB,2),(RosterSlot.FLEX,2),(RosterSlot.TE,2))),
])
def test_respects_any_real_configuration_without_fsffl_constants(count, slots):
    ref=HistoricalSeasonIdentity(league_family_id="family-x",league_id="provider-season-2023",season=2023)
    s=state(league_id=ref.league_id, season=ref.season, count=count,time=moment(2023),
            slots=slots,roster=22,scoring=(("pass_yd", .02),("rec",1.0)))
    out=inventory_historical_cutoff(season=ref,cutoff=moment(2023)+timedelta(days=8),
                                    snapshots=(s,),receipts=(),required_kinds=())
    assert out.team_count_observed==count
    assert out.team_count_declared==count
    assert out.lineup_slots==tuple((slot.value,n) for slot,n in slots)
    assert out.roster_size==22 and out.taxi_size==3 and out.ir_size==2
    assert out.rookie_draft_rounds==5 and not out.blockers


def test_two_seasons_same_family_may_have_different_league_ids_and_rules():
    refs=[HistoricalSeasonIdentity(league_family_id="continuing-family", league_id=f"season-{yr}", season=yr) for yr in (2022,2023)]
    s22=state(league_id=refs[0].league_id,season=2022,count=10,time=moment(2022),
              slots=((RosterSlot.QB,1),),roster=16,scoring=(("rec",.5),))
    s23=state(league_id=refs[1].league_id,season=2023,count=14,time=moment(2023),
              slots=((RosterSlot.SUPERFLEX,1),(RosterSlot.WR,4)),roster=24,scoring=(("rec",1.0),))
    a=inventory_historical_cutoff(season=refs[0],cutoff=moment(2022)+timedelta(days=1),snapshots=(s22,),receipts=(),required_kinds=())
    b=inventory_historical_cutoff(season=refs[1],cutoff=moment(2023)+timedelta(days=1),snapshots=(s23,),receipts=(),required_kinds=())
    assert a.season.league_family_id==b.season.league_family_id
    assert a.rule_fingerprint!=b.rule_fingerprint
    assert (a.team_count_declared,b.team_count_declared)==(10,14)
    assert (a.scoring_rules,b.scoring_rules)==((("rec",.5),),(("rec",1.0),))
    with pytest.raises(ValueError, match="different league or season"):
        inventory_historical_cutoff(season=refs[0],cutoff=moment(2023),snapshots=(s22,s23),receipts=(),required_kinds=())


def test_no_future_snapshot_or_source_leaks_into_point_in_time():
    ref=HistoricalSeasonIdentity(league_family_id="f", league_id="a", season=2023)
    pre=state(league_id="a",season=2023,count=12,time=moment(2023),slots=(),roster=20,scoring=(("rec",.5),))
    post=state(league_id="a",season=2023,count=12,time=moment(2023)+timedelta(days=2),
               slots=(),roster=20,scoring=(("rec",1.0),))
    r=receipt(ref, Kind.FORECAST, "future-forecast",effective=moment(2023),available=moment(2023)+timedelta(days=1))
    at=inventory_historical_cutoff(season=ref,cutoff=moment(2023)+timedelta(hours=1),
                                   snapshots=(pre,post),receipts=(r,),required_kinds=(Kind.FORECAST,))
    assert at.state_id==pre.state_id
    assert at.scoring_rules==(("rec",.5),)
    assert at.findings[0].status=="only_future_evidence"
    assert at.blockers==("forecast:only_future_evidence",)
    assert not at.requested_evidence_present


def test_backfilled_data_without_historical_publication_proof_stays_unverified():
    ref=HistoricalSeasonIdentity(league_family_id="f",league_id="a",season=2022)
    s=state(league_id="a",season=2022,count=8,time=moment(2022),slots=(),roster=20,scoring=())
    r=receipt(ref,Kind.MARKET,"unknown-release",available=None)
    out=inventory_historical_cutoff(season=ref,cutoff=moment(2022)+timedelta(days=1),
                                   snapshots=(s,),receipts=(r,),required_kinds=(Kind.MARKET,))
    assert out.findings[0].status=="unverified"
    assert not out.requested_evidence_present


def test_missing_past_snapshot_not_replaced_by_present_day_league():
    ref=HistoricalSeasonIdentity(league_family_id="family",league_id="2022-league",season=2022)
    out=inventory_historical_cutoff(season=ref,cutoff=moment(2022),snapshots=(),receipts=(),required_kinds=(Kind.TRANSACTIONS,Kind.MARKET))
    assert out.state_id is None and out.team_count_declared is None
    assert out.blockers==("no_same_season_state_at_cutoff","market:missing","transactions:missing")


def test_same_time_utc_offset_determinism_and_verified_archived_late_ingest():
    ref=HistoricalSeasonIdentity(league_family_id="f",league_id="l",season=2023)
    s=state(league_id="l",season=2023,count=12,time=moment(2023),slots=(),roster=20,scoring=())
    r=receipt(ref,Kind.FORECAST,"archived-pit",available=moment(2023),basis="verified_archive")
    ts=moment(2023)+timedelta(hours=1)
    a=inventory_historical_cutoff(season=ref,cutoff=ts,snapshots=(s,),receipts=(r,),required_kinds=(Kind.FORECAST,))
    b=inventory_historical_cutoff(season=ref,cutoff=ts.astimezone(timezone(timedelta(hours=-4))),snapshots=(s,),receipts=(r,),required_kinds=(Kind.FORECAST,))
    assert a==b
    assert a.findings[0].eligible_evidence_ids==("archived-pit",)


def test_cross_league_receipt_and_duplicate_id_fail_closed():
    ref=HistoricalSeasonIdentity(league_family_id="f",league_id="x",season=2023)
    other=HistoricalSeasonIdentity(league_family_id="another-family",league_id="x",season=2023)
    r=receipt(other,Kind.TRANSACTIONS,"x",available=moment(2023))
    with pytest.raises(ValueError,match="different league family"):
        inventory_historical_cutoff(season=ref,cutoff=moment(2023),snapshots=(),receipts=(r,),required_kinds=())
    r2=receipt(ref,Kind.TRANSACTIONS,"x",available=moment(2023))
    with pytest.raises(ValueError,match="duplicate evidence IDs"):
        inventory_historical_cutoff(season=ref,cutoff=moment(2023),snapshots=(),receipts=(r2,r2),required_kinds=())


def test_unverified_future_records_and_missing_are_distinguished():
    ref=HistoricalSeasonIdentity(league_family_id="f",league_id="l",season=2024)
    r=receipt(ref,Kind.DRAFT,"x",effective=moment(2024)+timedelta(days=4),available=moment(2024)+timedelta(days=4))
    out=inventory_historical_cutoff(season=ref,cutoff=moment(2024),snapshots=(),receipts=(r,),required_kinds=(Kind.DRAFT,Kind.OWNER_IDENTITY))
    assert [(f.kind,f.status) for f in out.findings]==[(Kind.DRAFT,"only_future_evidence"),(Kind.OWNER_IDENTITY,"missing")]


def test_evidence_requires_verifiable_availability_and_timezone():
    ref=HistoricalSeasonIdentity(league_family_id="f",league_id="l",season=2024)
    with pytest.raises(ValueError, match="requires a proof basis"):
        HistoricalEvidenceReceipt(season=ref,kind=Kind.MARKET,evidence_id="x",
                                  effective_at=moment(2024),available_at=moment(2024),
                                  availability_basis=None,source="fixture-provider")
    with pytest.raises(ValueError, match="requires a proof basis"):
        HistoricalEvidenceReceipt(season=ref,kind=Kind.MARKET,evidence_id="x",
                                  effective_at=moment(2024),available_at=None,
                                  availability_basis="verified_archive",source="fixture-provider")
    with pytest.raises(ValueError,match="historical cutoff"):
        inventory_historical_cutoff(season=ref,cutoff=datetime(2024,9,1),snapshots=(),receipts=(),required_kinds=())
