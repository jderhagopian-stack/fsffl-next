from datetime import UTC, datetime

from fsffl.state.draft_order_policy import (
    DraftOrderPolicyEvidence,
    DraftOrderPolicyParameter,
    resolve_draft_order_policy,
)
from fsffl.state.models import Provenance, ProviderRef


def _prov(effective_at: datetime) -> Provenance:
    return Provenance(
        source="verified-league-config",
        retrieved_at=effective_at,
        effective_at=effective_at,
        provider_ref=ProviderRef(provider="config", external_id="league-policy"),
        source_version="1",
    )


def _policy(*, version: str, effective_at: datetime, available_at: datetime):
    return DraftOrderPolicyEvidence(
        league_id="league-generic",
        draft_season=2027,
        effective_at=effective_at,
        available_at=available_at,
        policy_id="rookie-order",
        version=version,
        mechanism="custom-league-rule",
        description="verified league-specific rookie draft ordering rule",
        parameters=(DraftOrderPolicyParameter(name="non_playoff_metric", value="max_pf"),),
        provenance=_prov(effective_at),
    )


def test_policy_resolution_uses_latest_effective_and_knowable_version():
    early = _policy(
        version="1",
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    later = _policy(
        version="2",
        effective_at=datetime(2026, 7, 1, tzinfo=UTC),
        available_at=datetime(2026, 7, 2, tzinfo=UTC),
    )
    resolved = resolve_draft_order_policy(
        (early, later),
        league_id="league-generic",
        draft_season=2027,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    )
    assert resolved == later


def test_policy_resolution_does_not_leak_rule_learned_after_as_of():
    future_known = _policy(
        version="2",
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    assert resolve_draft_order_policy(
        (future_known,),
        league_id="league-generic",
        draft_season=2027,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    ) is None


def test_policy_resolution_does_not_cross_leagues_or_seasons():
    policy = _policy(
        version="1",
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert resolve_draft_order_policy(
        (policy,),
        league_id="other-league",
        draft_season=2027,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    ) is None
    assert resolve_draft_order_policy(
        (policy,),
        league_id="league-generic",
        draft_season=2028,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
    ) is None
