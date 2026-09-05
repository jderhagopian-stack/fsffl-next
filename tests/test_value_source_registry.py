import pytest

from fsffl.value.calibration import DataRightsClass
from fsffl.value.source_registry import (
    MarketSignalKind,
    MarketSourceDefinition,
    MarketSourceRegistry,
    MarketSourceStatus,
)


def test_registry_tracks_lineage_without_double_counting_derivatives() -> None:
    fantasypros = MarketSourceDefinition(
        source_id="fantasypros-ecr",
        display_name="FantasyPros Dynasty ECR",
        signal_kind=MarketSignalKind.CONSENSUS_RANKING,
        rights_class=DataRightsClass.RESEARCH_ONLY,
        status=MarketSourceStatus.RESEARCH_CANDIDATE,
    )
    dynastyprocess = MarketSourceDefinition(
        source_id="dynastyprocess-values",
        display_name="DynastyProcess Values",
        signal_kind=MarketSignalKind.MARKET_INDEX,
        rights_class=DataRightsClass.PUBLIC_REDISTRIBUTABLE,
        status=MarketSourceStatus.ELIGIBLE,
        parent_source_ids=("fantasypros-ecr",),
    )
    registry = MarketSourceRegistry(
        sources=(fantasypros, dynastyprocess),
        registry_version="next3-market-sources-v1",
    )

    assert registry.independent_roots("dynastyprocess-values") == ("fantasypros-ecr",)


def test_registry_rejects_dependency_cycles() -> None:
    a = MarketSourceDefinition(
        source_id="a",
        display_name="A",
        signal_kind=MarketSignalKind.OTHER,
        rights_class=DataRightsClass.UNKNOWN,
        status=MarketSourceStatus.RESEARCH_CANDIDATE,
        parent_source_ids=("b",),
    )
    b = MarketSourceDefinition(
        source_id="b",
        display_name="B",
        signal_kind=MarketSignalKind.OTHER,
        rights_class=DataRightsClass.UNKNOWN,
        status=MarketSourceStatus.RESEARCH_CANDIDATE,
        parent_source_ids=("a",),
    )
    with pytest.raises(ValueError, match="acyclic"):
        MarketSourceRegistry(sources=(a, b), registry_version="v1")


def test_comparator_only_source_is_not_authoritative_candidate() -> None:
    ktc = MarketSourceDefinition(
        source_id="ktc",
        display_name="KeepTradeCut",
        signal_kind=MarketSignalKind.CROWD_PREFERENCE,
        rights_class=DataRightsClass.RUNTIME_ONLY,
        status=MarketSourceStatus.COMPARATOR_ONLY,
    )
    fantasycalc = MarketSourceDefinition(
        source_id="fantasycalc",
        display_name="FantasyCalc",
        signal_kind=MarketSignalKind.REVEALED_TRANSACTION,
        rights_class=DataRightsClass.UNKNOWN,
        status=MarketSourceStatus.RESEARCH_CANDIDATE,
    )
    registry = MarketSourceRegistry(
        sources=(ktc, fantasycalc),
        registry_version="next3-market-sources-v1",
    )

    assert registry.authoritative_candidates() == ()
