"""Provider-neutral league-season crosswalk; different team counts/rules/yearly IDs."""
from datetime import UTC, datetime, timedelta

import pytest

from fsffl.state.historical_coverage import HistoricalEvidenceKind as Kind, HistoricalEvidenceReceipt as Receipt, HistoricalSeasonIdentity as Season
from fsffl.state.historical_season_lineage import (
    HistoricalRosterBinding as Binding, HistoricalSeasonSource as Source,
    HistoricalSeasonLink as Link, SeasonLinkProof, build_historical_season_lineage,
)
from fsffl.state.models import ProviderRef


def stamp(y: int):
    return datetime(y, 8, 1, tzinfo=UTC)


def receipt(s: Season, kind: Kind, eid: str):
    return Receipt(season=s, kind=kind, evidence_id=eid, effective_at=stamp(s.season),
                   available_at=stamp(s.season), availability_basis="provider_timestamp", source="archive")


def source(y, teams=12, provider_id=None, family="family-one", slots=("QB", "WR", "FLEX")):
    s=Season(league_family_id=family, league_id=f"provider:{provider_id or y}", season=y)
    return Source(season=s, provider_ref=ProviderRef(provider="x-provider",external_id=str(provider_id or y)),
                  settings_receipt=receipt(s,Kind.SETTINGS,f"config-{y}"), observed_team_count=teams,
                  roster_bindings=tuple(Binding(provider_roster_id=f"{i}",canonical_team_id=f"season-{y}-team-{i}",
                                                provider_manager_id=f"owner-{i}") for i in range(teams)),
                  raw_position_or_slot_codes=slots)


@pytest.mark.parametrize("team_count,slots",[(2,("QB",)),(8,("QB","RB","K","DST")),
                                        (10,("WR","FLEX")),(12,("QB","SUPERFLEX","WR")),
                                        (14,("QB","TE")),(16,("QB","FLEX","SUPERFLEX"))])
def test_single_source_handles_varied_team_count_lineup(team_count, slots):
    x=source(2023, teams=team_count, slots=slots)
    result=build_historical_season_lineage(sources=(x,),links=())
    assert result.seasons==(x.season,)
    assert result.root_or_unlinked_seasons==(x.season,)
    assert x.roster_mapping_status=="complete_mapping_only"
    assert x.unknown_slot_codes==()
    assert x.source_content_sha256 is None  # inventory, not a source-authority promotion


def test_verified_explicit_previous_provider_id_links_seasons_without_joining_roster_names():
    a=source(2022,teams=8,provider_id="old",slots=("QB","RB"))
    b=source(2023,teams=16,provider_id="new",slots=("QB","WR","SUPERFLEX"))
    link=Link(previous=a.season,current=b.season,previous_provider_ref=a.provider_ref,
              observed_parent_provider_league_id="old",evidence=receipt(b.season,Kind.OWNER_IDENTITY,"previous-id"),
              proof=SeasonLinkProof.PROVIDER_PREVIOUS_LEAGUE)
    out=build_historical_season_lineage(sources=(b,a),links=(link,))
    assert out.seasons==(a.season,b.season)
    assert out.root_or_unlinked_seasons==(a.season,)
    assert out.links==(link,)
    assert len(a.roster_bindings)!=len(b.roster_bindings)


def test_no_silent_owner_mapping_from_identical_manager_or_team_names():
    a=source(2023, provider_id="A")
    b=source(2024, provider_id="B")
    out=build_historical_season_lineage(sources=(a,b),links=())
    assert out.links==() and set(out.root_or_unlinked_seasons)=={a.season,b.season}


def test_reject_provider_identity_collision_across_families():
    a=source(2023,provider_id="same",family="A")
    b=source(2024,provider_id="same",family="B")
    with pytest.raises(ValueError,match="duplicate/ambiguous"):
        build_historical_season_lineage(sources=(a,b),links=())


def test_different_leagues_may_have_same_provider_roster_ids():
    a=source(2023,provider_id="A",family="f1")
    b=source(2023,provider_id="B",family="f2")
    result=build_historical_season_lineage(sources=(a,b),links=())
    assert len(result.seasons)==2


def test_link_parent_proof_requires_exact_provider_id_and_known_availability():
    a=source(2022,provider_id="A")
    b=source(2023,provider_id="B")
    with pytest.raises(ValueError,match="parent ID"):
        Link(previous=a.season,current=b.season,previous_provider_ref=a.provider_ref,
             observed_parent_provider_league_id="C",evidence=receipt(b.season,Kind.OWNER_IDENTITY,"p"),
             proof=SeasonLinkProof.PROVIDER_PREVIOUS_LEAGUE)
    missing=Receipt(season=b.season,kind=Kind.OWNER_IDENTITY,evidence_id="unknown",effective_at=stamp(2023),source="unknown")
    with pytest.raises(ValueError,match="documented source availability"):
        Link(previous=a.season,current=b.season,previous_provider_ref=a.provider_ref,
             observed_parent_provider_league_id="A",evidence=missing,proof=SeasonLinkProof.VERIFIED_ARCHIVE)


def test_reject_forked_or_invalid_history_and_cross_family():
    a=source(2022,provider_id="A")
    b=source(2023,provider_id="B")
    c=source(2024,provider_id="C")
    def link(p,n):
        return Link(previous=p.season,current=n.season,previous_provider_ref=p.provider_ref,
                    observed_parent_provider_league_id=p.provider_ref.external_id,
                    evidence=receipt(n.season,Kind.OWNER_IDENTITY,"id"+str(n.season)),
                    proof=SeasonLinkProof.PROVIDER_PREVIOUS_LEAGUE)
    with pytest.raises(ValueError,match="ambiguous fork"):
        build_historical_season_lineage(sources=(a,b,c),links=(link(a,b),link(a,c)))
    with pytest.raises(ValueError,match="must precede"):
        link(b,a)
    d=source(2025,provider_id="D",family="other")
    with pytest.raises(ValueError,match="cross-family"):
        link(c,d)


def test_exposes_unsupported_idp_formats_instead_of_silent_coercion():
    x=source(2025,slots=("QB","LB","DB","IDP_FLEX"))
    assert x.unknown_slot_codes==("DB","IDP_FLEX","LB")
    assert x.roster_mapping_status=="unsupported_position_or_slot"
    p=source(2025,teams=8)
    p=p.model_copy(update={"observed_team_count":9})
    assert p.roster_mapping_status=="partial_roster_crosswalk"


def test_reject_duplicate_roster_map_or_source_receipt_wrong_kind():
    a=source(2023,teams=2)
    with pytest.raises(ValueError,match="unique"):
        Source(season=a.season,provider_ref=a.provider_ref,settings_receipt=a.settings_receipt,
               roster_bindings=(a.roster_bindings[0],a.roster_bindings[0]))
    with pytest.raises(ValueError,match="settings evidence"):
        Source(season=a.season,provider_ref=a.provider_ref,
               settings_receipt=receipt(a.season,Kind.TRANSACTIONS,"wrong"))
