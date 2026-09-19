from __future__ import annotations

from fsffl.value.models import AssetValueProfile, MarketPriceEstimate, ValueDistribution


def cardinal_market_profiles(value_evidence) -> dict[str, AssetValueProfile]:
    """Adapt authoritative NEXT-3 cardinal scores into typed market estimates.

    This is a Product-layer type adapter only. It performs no rescaling, weighting,
    recommendation, or package adjustment; the exact authoritative 0-10,000 FSFFL
    cardinal score is preserved for NEXT-5 economics consumers.
    """

    profiles: dict[str, AssetValueProfile] = {}
    if value_evidence is None:
        return profiles
    for score in value_evidence.fsffl_cardinal_values:
        estimate = MarketPriceEstimate(
            asset_id=score.asset_id,
            asset_kind=score.asset_kind,
            distribution=ValueDistribution(mean=score.score, stddev=0.0),
            scale=score.scale,
            as_of=score.as_of,
            market_context_id=score.market_context_id,
            model_version=score.model_version,
            evidence_sources=(score.evidence_source_id,),
        )
        profiles[score.asset_id] = AssetValueProfile(
            asset_id=score.asset_id,
            asset_kind=score.asset_kind,
            market_price=estimate,
        )
    return profiles
