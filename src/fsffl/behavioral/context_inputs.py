"""Model-specific partial inputs; never manufacture a historical LeagueState.

Projection is the existing multiclass context formula. Unknown facts remain None;
a readiness report is not permission to publish an owner preference or PIT grade.
Source adapters remain responsible for identity, clocks and field evidence.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Protocol

POSITIONS = ('QB', 'RB', 'WR', 'TE')
POSITION_FEATURES = ('relative_rostered_count', 'relative_active_count',
                     'active_above_starter_requirement', 'direct_starter_requirement')
FEATURE_NAMES = tuple(f'{p}.{name}' for p in POSITIONS for name in POSITION_FEATURES) + (
    'flex_slot_count', 'superflex_slot_count', 'roster_size', 'active_roster_size', 'owned_pick_count')


class PositionInput(Protocol):
    position: object
    rostered_count: int | None
    active_rostered_count: int | None
    direct_starter_requirement: int | None
    league_average_rostered_count: float | None
    league_average_active_rostered_count: float | None


class ContextInput(Protocol):
    positions: tuple[PositionInput, ...]
    flex_slot_count: int | None
    superflex_slot_count: int | None
    roster_size: int | None
    active_roster_size: int | None
    owned_pick_count: int | None


@dataclass(frozen=True)
class PartialPositionContext:
    position: str
    rostered_count: int | None = None
    active_rostered_count: int | None = None
    direct_starter_requirement: int | None = None
    league_average_rostered_count: float | None = None
    league_average_active_rostered_count: float | None = None


@dataclass(frozen=True)
class PartialRosterContext:
    positions: tuple[PartialPositionContext, ...] = ()
    flex_slot_count: int | None = None
    superflex_slot_count: int | None = None
    roster_size: int | None = None
    active_roster_size: int | None = None
    owned_pick_count: int | None = None


@dataclass(frozen=True)
class ContextFeatureReadiness:
    values: tuple[float | None, ...]
    missing_features: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.missing_features

    def require_complete(self) -> tuple[float, ...]:
        if not self.complete:
            raise ValueError('context model inputs unavailable: ' + ', '.join(self.missing_features))
        return tuple(self.values)


def _number(value, *, count=False):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        raise ValueError('context facts must be finite nonnegative numbers or unknown')
    if count and int(value) != value:
        raise ValueError('context counts must be integers')
    return value


def context_feature_readiness(context: ContextInput) -> ContextFeatureReadiness:
    """One accepted21-feature projection for full or explicitly partial facts.

    This checks numerical sufficiency only. It does not certify source dates,
    complete ledgers, player identities, contextual quality or competitive state.
    No FAAB, market/Forecast or owner-choice outcome is an input to this model.
    """
    by_position = {}
    for row in context.positions:
        position = getattr(row.position, 'value', row.position)
        if position in by_position:
            raise ValueError('duplicate context position')
        by_position[position] = row
    values = []
    for position in POSITIONS:
        row = by_position.get(position)
        if row is None:
            values.extend((None,) * 4)
            continue
        rostered = _number(row.rostered_count, count=True)
        active = _number(row.active_rostered_count, count=True)
        starters = _number(row.direct_starter_requirement, count=True)
        average = _number(row.league_average_rostered_count)
        active_average = _number(row.league_average_active_rostered_count)
        if active is not None and rostered is not None and active > rostered:
            raise ValueError('active context count exceeds rostered count')
        values.extend((rostered-average if rostered is not None and average is not None else None,
            active-active_average if active is not None and active_average is not None else None,
            active-starters if active is not None and starters is not None else None,
            float(starters) if starters is not None else None))
    for name in FEATURE_NAMES[-5:]:
        value = _number(getattr(context, name), count=True)
        values.append(float(value) if value is not None else None)
    if (context.active_roster_size is not None and context.roster_size is not None
            and context.active_roster_size > context.roster_size):
        raise ValueError('active roster size exceeds roster size')
    return ContextFeatureReadiness(tuple(values), tuple(name for name, value in zip(FEATURE_NAMES, values)
        if value is None))
