from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel
from fsffl.team_utility.utility import OwnerStrategicPosture


class ProductRoute(StrEnum):
    LEAGUE = "league"
    MY_TEAM = "my_team"
    TRADE_CENTER = "trade_center"
    OPPORTUNITIES = "opportunities"
    ANALYTICS = "analytics"
    REPORTS = "reports"


class ProductAction(StrEnum):
    SELECT_LEAGUE = "select_league"
    SELECT_TEAM = "select_team"
    SET_OWNER_POSTURE = "set_owner_posture"
    BUILD_TRADE = "build_trade"
    EVALUATE_TRADE = "evaluate_trade"
    EXPLORE_PRICE = "explore_price"
    FIND_OPPORTUNITIES = "find_opportunities"
    SHOP_ASSET = "shop_asset"
    EVALUATE_WAIVER = "evaluate_waiver"
    GENERATE_REPORT = "generate_report"


class ProductStatusKind(StrEnum):
    INFO = "info"
    WARNING = "warning"
    PROVISIONAL = "provisional"
    ERROR = "error"


class ProductStatus(FrozenModel):
    kind: ProductStatusKind
    code: str
    message: str

    @model_validator(mode="after")
    def validate_text(self) -> "ProductStatus":
        if not self.code.strip() or not self.message.strip():
            raise ValueError("product status code/message cannot be blank")
        return self


class ProductContext(FrozenModel):
    user_id: str
    league_id: str | None = None
    team_id: str | None = None
    owner_posture: OwnerStrategicPosture | None = None
    state_id: str | None = None
    evidence_as_of: datetime | None = None
    statuses: tuple[ProductStatus, ...] = ()
    product_version: str = "next8-product-v1"

    @field_validator("evidence_as_of")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("evidence_as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_context(self) -> "ProductContext":
        if not self.user_id.strip() or not self.product_version.strip():
            raise ValueError("product context identifiers cannot be blank")
        if self.team_id is not None and self.league_id is None:
            raise ValueError("team selection requires selected league")
        if self.state_id is not None and self.league_id is None:
            raise ValueError("state identity requires selected league")
        return self


class NavigationItem(FrozenModel):
    route: ProductRoute
    label: str
    requires_league: bool = True
    requires_team: bool = False

    @model_validator(mode="after")
    def validate_label(self) -> "NavigationItem":
        if not self.label.strip():
            raise ValueError("navigation label cannot be blank")
        return self


PRIMARY_NAVIGATION: tuple[NavigationItem, ...] = (
    NavigationItem(route=ProductRoute.LEAGUE, label="League"),
    NavigationItem(route=ProductRoute.MY_TEAM, label="My Team", requires_team=True),
    NavigationItem(route=ProductRoute.TRADE_CENTER, label="Trade Center", requires_team=True),
    NavigationItem(route=ProductRoute.OPPORTUNITIES, label="Opportunities", requires_team=True),
    NavigationItem(route=ProductRoute.ANALYTICS, label="Analytics"),
    NavigationItem(route=ProductRoute.REPORTS, label="Reports"),
)


def available_navigation(context: ProductContext) -> tuple[NavigationItem, ...]:
    return tuple(
        item
        for item in PRIMARY_NAVIGATION
        if (not item.requires_league or context.league_id is not None)
        and (not item.requires_team or context.team_id is not None)
    )
