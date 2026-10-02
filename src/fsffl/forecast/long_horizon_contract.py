from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position

from .future_contract import CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE


LONG_HORIZON_FORECAST_CONTRACT_VERSION = (
    "long-horizon-forecast-authority-v1:y4-y7:symmetric-policy-envelope"
)
LONG_HORIZON_AUTHORITY_MAP_VERSION = "y4-y7-symmetric-authority-20260927-v1"
LONG_HORIZON_POLICIES = (
    "baseline",
    "hard_router",
    "soft_stack",
    "blanket_75_25",
)
LongHorizonPolicyId = Literal[
    "baseline",
    "hard_router",
    "soft_stack",
    "blanket_75_25",
]
LongHorizonYearIndex = Literal[4, 5, 6, 7]

# Frozen from the accepted symmetric Y4-Y7 authority map. These sets determine
# which global-policy Shapley results may contribute to a player's Value authority.
# Forecast transport still carries all four policies because the accepted research
# calculated each policy against a coherent league-wide policy board before
# applying the player-position authority filter.
_LONG_HORIZON_SUPPORTED_POLICIES: dict[tuple[Position, int], tuple[str, ...]] = {
    (Position.QB, 4): ("blanket_75_25", "soft_stack"),
    (Position.RB, 4): ("baseline", "blanket_75_25", "hard_router", "soft_stack"),
    (Position.WR, 4): ("blanket_75_25", "soft_stack"),
    (Position.TE, 4): ("baseline", "blanket_75_25", "hard_router", "soft_stack"),
    (Position.QB, 5): ("blanket_75_25",),
    (Position.RB, 5): ("baseline", "blanket_75_25"),
    (Position.WR, 5): ("hard_router",),
    (Position.TE, 5): ("baseline", "blanket_75_25", "hard_router", "soft_stack"),
    (Position.QB, 6): ("blanket_75_25", "soft_stack"),
    (Position.RB, 6): ("baseline", "blanket_75_25"),
    (Position.WR, 6): ("blanket_75_25", "hard_router", "soft_stack"),
    (Position.TE, 6): ("blanket_75_25", "hard_router", "soft_stack"),
    (Position.QB, 7): ("blanket_75_25", "hard_router", "soft_stack"),
    (Position.RB, 7): ("hard_router", "soft_stack"),
    (Position.WR, 7): ("hard_router", "soft_stack"),
    (Position.TE, 7): ("baseline", "blanket_75_25", "soft_stack"),
}


def supported_long_horizon_policies(
    position: Position,
    year_index: int,
) -> tuple[str, ...]:
    try:
        return _LONG_HORIZON_SUPPORTED_POLICIES[(position, int(year_index))]
    except KeyError as exc:
        raise ValueError(
            f"Long-Horizon Forecast authority is unavailable for {position.value} Y{year_index}"
        ) from exc


def _authority_map_payload() -> list[dict[str, object]]:
    return [
        {
            "position": position.value,
            "year_index": year_index,
            "supported_policies": list(policies),
            "exact": len(policies) == 1,
        }
        for (position, year_index), policies in sorted(
            _LONG_HORIZON_SUPPORTED_POLICIES.items(),
            key=lambda item: (item[0][1], item[0][0].value),
        )
    ]


LONG_HORIZON_AUTHORITY_MAP_SHA256 = (
    "487555fac2e5fd0823c6a70d29b1c1e60fbf2adc0e1bb8140f9f43e6ee0e9e00"
)
_COMPUTED_LONG_HORIZON_AUTHORITY_MAP_SHA256 = hashlib.sha256(
    json.dumps(
        _authority_map_payload(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
).hexdigest()
if _COMPUTED_LONG_HORIZON_AUTHORITY_MAP_SHA256 != LONG_HORIZON_AUTHORITY_MAP_SHA256:
    raise RuntimeError(
        "frozen long-horizon Forecast authority map no longer matches its governed hash"
    )


class LongHorizonPolicyForecast(FrozenModel):
    """One policy-specific annual Forecast used by the frozen Y4-Y7 authority map."""

    player_id: str
    position: Position
    evaluation_season: Annotated[int, Field(ge=2000)]
    year_index: LongHorizonYearIndex
    target_season: Annotated[int, Field(ge=2000)]
    policy_id: LongHorizonPolicyId
    central_expectation: Annotated[float, Field(ge=0.0)]
    absolute_error_80: Annotated[float, Field(ge=0.0)]
    absolute_error_90: Annotated[float, Field(ge=0.0)]
    scoring_coordinate: str = CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
    model_version: str
    source: str
    evidence_path: str

    @field_validator(
        "player_id",
        "scoring_coordinate",
        "model_version",
        "source",
        "evidence_path",
    )
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("long-horizon Forecast identifiers cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_row(self) -> "LongHorizonPolicyForecast":
        if self.target_season != self.evaluation_season + self.year_index - 1:
            raise ValueError("long-horizon target season must align with year_index")
        if self.absolute_error_90 < self.absolute_error_80:
            raise ValueError("90% long-horizon error band cannot be narrower than 80%")
        return self


class LongHorizonForecastAuthorityContract(FrozenModel):
    """Forecast-owned Y4-Y7 transport preserving exact versus set-valued authority."""

    contract_version: str = LONG_HORIZON_FORECAST_CONTRACT_VERSION
    authority_map_version: str = LONG_HORIZON_AUTHORITY_MAP_VERSION
    authority_map_sha256: str = LONG_HORIZON_AUTHORITY_MAP_SHA256
    evaluation_season: Annotated[int, Field(ge=2000)]
    scoring_coordinate: str = CONNECTED_LEAGUE_FANTASY_POINTS_COORDINATE
    forecast_model_version: str
    forecast_source: str
    forecasts: tuple[LongHorizonPolicyForecast, ...]
    provenance: dict[str, bool | float | int | str | None] = Field(default_factory=dict)

    @field_validator(
        "contract_version",
        "authority_map_version",
        "authority_map_sha256",
        "scoring_coordinate",
        "forecast_model_version",
        "forecast_source",
    )
    @classmethod
    def require_contract_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("long-horizon Forecast contract identifiers cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_contract(self) -> "LongHorizonForecastAuthorityContract":
        if self.authority_map_version != LONG_HORIZON_AUTHORITY_MAP_VERSION:
            raise ValueError("long-horizon Forecast authority-map version is not governed")
        if self.authority_map_sha256 != LONG_HORIZON_AUTHORITY_MAP_SHA256:
            raise ValueError("long-horizon Forecast authority-map hash is not governed")
        if not self.forecasts:
            raise ValueError("long-horizon Forecast contract cannot be empty")

        by_player: dict[str, list[LongHorizonPolicyForecast]] = {}
        keys: set[tuple[str, int, str]] = set()
        for row in self.forecasts:
            if row.evaluation_season != self.evaluation_season:
                raise ValueError("long-horizon Forecast rows must share evaluation season")
            if row.scoring_coordinate != self.scoring_coordinate:
                raise ValueError("long-horizon Forecast rows must share scoring coordinate")
            key = (row.player_id, int(row.year_index), row.policy_id)
            if key in keys:
                raise ValueError(
                    "duplicate long-horizon Forecast player/year/policy row: "
                    f"{row.player_id} Y{row.year_index} {row.policy_id}"
                )
            keys.add(key)
            by_player.setdefault(row.player_id, []).append(row)

        expected_policies = set(LONG_HORIZON_POLICIES)
        for player_id, rows in by_player.items():
            positions = {row.position for row in rows}
            if len(positions) != 1:
                raise ValueError(
                    f"long-horizon Forecast player position must be stable: {player_id}"
                )
            position = next(iter(positions))
            by_year: dict[int, set[str]] = {}
            for row in rows:
                by_year.setdefault(int(row.year_index), set()).add(row.policy_id)
            if set(by_year) != {4, 5, 6, 7}:
                raise ValueError(
                    f"long-horizon Forecast requires complete Y4-Y7 coverage: {player_id}"
                )
            for year_index in (4, 5, 6, 7):
                if by_year[year_index] != expected_policies:
                    raise ValueError(
                        "long-horizon Forecast transport must carry all four frozen "
                        f"policies for {player_id} Y{year_index}"
                    )
                supported_long_horizon_policies(position, year_index)
        return self

    @property
    def player_ids(self) -> tuple[str, ...]:
        return tuple(sorted({row.player_id for row in self.forecasts}))

    def rows_for(
        self,
        *,
        player_id: str,
        year_index: int,
    ) -> tuple[LongHorizonPolicyForecast, ...]:
        return tuple(
            sorted(
                (
                    row
                    for row in self.forecasts
                    if row.player_id == player_id
                    and int(row.year_index) == int(year_index)
                ),
                key=lambda row: row.policy_id,
            )
        )
