from datetime import UTC, datetime

import pytest

from fsffl.product.models import ProductAction, ProductContext, ProductRoute
from fsffl.product.web_adapter import (
    AuthorizationDecision,
    ProductRequest,
    ProductResponse,
    ProductResponseStatus,
    RequestKind,
)


def _context(*, team: bool = True) -> ProductContext:
    return ProductContext(
        user_id="u1",
        league_id="l1",
        team_id="t1" if team else None,
        state_id="s1",
        evidence_as_of=datetime(2026, 9, 5, tzinfo=UTC),
    )


def test_team_scoped_route_requires_team_context() -> None:
    with pytest.raises(ValueError, match="team-scoped"):
        ProductRequest(
            request_id="r1",
            kind=RequestKind.QUERY,
            context=_context(team=False),
            route=ProductRoute.MY_TEAM,
        )


def test_query_cannot_smuggle_action() -> None:
    with pytest.raises(ValueError, match="query request cannot include"):
        ProductRequest(
            request_id="r1",
            kind=RequestKind.QUERY,
            context=_context(),
            route=ProductRoute.TRADE_CENTER,
            action=ProductAction.EVALUATE_TRADE,
        )


def test_action_requires_explicit_action_name() -> None:
    with pytest.raises(ValueError, match="requires an explicit"):
        ProductRequest(
            request_id="r1",
            kind=RequestKind.ACTION,
            context=_context(),
            route=ProductRoute.TRADE_CENTER,
        )


def test_success_response_cannot_hide_errors() -> None:
    with pytest.raises(ValueError, match="successful response"):
        ProductResponse(
            request_id="r1",
            status=ProductResponseStatus.OK,
            errors=("bad",),
        )


def test_failed_response_requires_explicit_error() -> None:
    with pytest.raises(ValueError, match="requires explicit errors"):
        ProductResponse(
            request_id="r1",
            status=ProductResponseStatus.FORBIDDEN,
        )


def test_denied_authorization_requires_reason() -> None:
    with pytest.raises(ValueError, match="requires a reason"):
        AuthorizationDecision(user_id="u1", allowed=False)
