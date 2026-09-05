from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import model_validator

from fsffl.state.models import FrozenModel

from .models import ProductAction, ProductContext, ProductRoute


class RequestKind(StrEnum):
    QUERY = "query"
    ACTION = "action"


class ProductRequest(FrozenModel):
    request_id: str
    kind: RequestKind
    context: ProductContext
    route: ProductRoute
    action: ProductAction | None = None
    payload: dict[str, Any] = {}
    product_api_version: str = "next8-web-adapter-v1"

    @model_validator(mode="after")
    def validate_request(self) -> "ProductRequest":
        if not self.request_id.strip() or not self.product_api_version.strip():
            raise ValueError("request identifiers cannot be blank")
        if self.kind == RequestKind.ACTION and self.action is None:
            raise ValueError("action request requires an explicit ProductAction")
        if self.kind == RequestKind.QUERY and self.action is not None:
            raise ValueError("query request cannot include ProductAction")
        if self.context.league_id is None:
            raise ValueError("product requests require selected league context")
        if self.route in {
            ProductRoute.MY_TEAM,
            ProductRoute.TRADE_CENTER,
            ProductRoute.OPPORTUNITIES,
        } and self.context.team_id is None:
            raise ValueError("team-scoped route requires selected team context")
        return self


class ProductResponseStatus(StrEnum):
    OK = "ok"
    INVALID_REQUEST = "invalid_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    UPSTREAM_INCOMPLETE = "upstream_incomplete"
    ERROR = "error"


class ProductResponse(FrozenModel):
    request_id: str
    status: ProductResponseStatus
    data: dict[str, Any] | None = None
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    product_api_version: str = "next8-web-adapter-v1"

    @model_validator(mode="after")
    def validate_response(self) -> "ProductResponse":
        if not self.request_id.strip() or not self.product_api_version.strip():
            raise ValueError("response identifiers cannot be blank")
        if self.status == ProductResponseStatus.OK and self.errors:
            raise ValueError("successful response cannot carry errors")
        if self.status != ProductResponseStatus.OK and not self.errors:
            raise ValueError("non-success response requires explicit errors")
        return self


class AuthorizationDecision(FrozenModel):
    user_id: str
    allowed: bool
    reason: str | None = None

    @model_validator(mode="after")
    def validate_authorization(self) -> "AuthorizationDecision":
        if not self.user_id.strip():
            raise ValueError("authorization user_id cannot be blank")
        if not self.allowed and (self.reason is None or not self.reason.strip()):
            raise ValueError("denied authorization requires a reason")
        return self


class ProductAuthorizer:
    """Boundary interface for private-beta authorization.

    Concrete hosting/auth providers implement this outside model authority.
    """

    def authorize(self, context: ProductContext) -> AuthorizationDecision:
        raise NotImplementedError


class ProductQueryBackend:
    """Thin adapter interface over NEXT-7 read-only analytics/report contracts."""

    def query(self, request: ProductRequest) -> ProductResponse:
        raise NotImplementedError


class ProductActionBackend:
    """Explicit invocation boundary for application actions.

    Actions may call authoritative upstream workflows. They may not mutate model
    authority inside the product layer.
    """

    def execute(self, request: ProductRequest) -> ProductResponse:
        raise NotImplementedError
