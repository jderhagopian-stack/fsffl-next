from __future__ import annotations

from .calibration import DataRightsClass
from .source_registry import (
    MarketSignalKind,
    MarketSourceDefinition,
    MarketSourceRegistry,
    MarketSourceStatus,
)


def next3_market_source_registry_v1() -> MarketSourceRegistry:
    """Return the governed initial broader-market source/lineage catalog.

    The two abstract roots are evidence families, not ingestible providers. The
    three trade-derived services are conservatively collapsed to one revealed-
    transaction family vote for authority until more granular corpus-overlap
    evidence justifies treating any of them as independent roots.
    """

    return MarketSourceRegistry(
        registry_version="next3-market-sources-v1",
        sources=(
            MarketSourceDefinition(
                source_id="fantasypros_dynasty_consensus_root",
                display_name="FantasyPros dynasty consensus evidence root",
                signal_kind=MarketSignalKind.CONSENSUS_RANKING,
                rights_class=DataRightsClass.UNKNOWN,
                status=MarketSourceStatus.COMPARATOR_ONLY,
                notes=(
                    "Abstract lineage root. DynastyProcess market values are derived "
                    "from FantasyPros dynasty consensus ranks."
                ),
            ),
            MarketSourceDefinition(
                source_id="revealed_dynasty_transactions_root",
                display_name="Revealed dynasty transaction evidence root",
                signal_kind=MarketSignalKind.REVEALED_TRANSACTION,
                rights_class=DataRightsClass.UNKNOWN,
                status=MarketSourceStatus.COMPARATOR_ONLY,
                notes=(
                    "Abstract conservative evidence-family root. Trade-derived providers "
                    "may use different corpora and models, but are not granted separate "
                    "authoritative votes until overlap is quantified."
                ),
            ),
            MarketSourceDefinition(
                source_id="dynastyprocess_market_values",
                display_name="DynastyProcess market values",
                signal_kind=MarketSignalKind.CONSENSUS_RANKING,
                rights_class=DataRightsClass.RESEARCH_ONLY,
                status=MarketSourceStatus.ELIGIBLE,
                parent_source_ids=("fantasypros_dynasty_consensus_root",),
                notes=(
                    "Consensus-derived comparator/market signal. Runtime acquisition and "
                    "redistribution remain governed separately from predictive usefulness."
                ),
            ),
            MarketSourceDefinition(
                source_id="dynastydealer_market_values",
                display_name="Dynasty Dealer market values",
                signal_kind=MarketSignalKind.REVEALED_TRANSACTION,
                rights_class=DataRightsClass.RUNTIME_ONLY,
                status=MarketSourceStatus.ELIGIBLE,
                parent_source_ids=("revealed_dynasty_transactions_root",),
                notes="Trade-derived market signal; attribution/rights remain provider-governed.",
            ),
            MarketSourceDefinition(
                source_id="fantasycalc_market_values",
                display_name="FantasyCalc market values",
                signal_kind=MarketSignalKind.REVEALED_TRANSACTION,
                rights_class=DataRightsClass.RUNTIME_ONLY,
                status=MarketSourceStatus.ELIGIBLE,
                parent_source_ids=("revealed_dynasty_transactions_root",),
                notes=(
                    "Trade-derived market signal. Conservatively shares one authoritative "
                    "evidence-family vote with other trade-derived providers in v1."
                ),
            ),
            MarketSourceDefinition(
                source_id="statsguy_market_values",
                display_name="Stats Guy Fantasy market values",
                signal_kind=MarketSignalKind.REVEALED_TRANSACTION,
                rights_class=DataRightsClass.RUNTIME_ONLY,
                status=MarketSourceStatus.ELIGIBLE,
                parent_source_ids=("revealed_dynasty_transactions_root",),
                notes=(
                    "Trade-derived market signal. Historical snapshots support chronological "
                    "diagnostics; v1 conservatively shares the transaction-family vote."
                ),
            ),
        ),
    )
