"""Explicit age dates at the Forecast feature boundary, without changing source facts."""
from __future__ import annotations

from datetime import date, datetime
import math


FORECAST_ORIGIN_AGE_VERSION = "forecast-origin-age-v1"
AGE_YEAR_DAYS = 365.2425


def age_at_forecast_origin(
    *,
    evaluation_season: int,
    source_age_years: float,
    source_age_as_of: date | None,
    birth_date: date | None = None,
) -> float:
    """Use the accepted September-1 base-season convention.

    A dated source age can advance without inventing a birthday. DOB takes
    precedence when available; missing DOB never becomes an observed zero age.
    The original source coordinate remains the caller's immutable evidence.
    """
    origin = date(evaluation_season, 9, 1)
    if not math.isfinite(source_age_years) or source_age_years < 0:
        raise ValueError("source age must be finite and nonnegative")
    if birth_date is not None:
        if birth_date > origin:
            raise ValueError("birth date is after the forecast origin")
        return (origin - birth_date).days / AGE_YEAR_DAYS
    if source_age_as_of is None:
        raise ValueError("age requires a governed DOB or an explicit age-as-of date")
    result = source_age_years + (origin - source_age_as_of).days / AGE_YEAR_DAYS
    if not math.isfinite(result) or result < 0:
        raise ValueError("dated source age is invalid at the forecast origin")
    return result


def age_date(value: object) -> date | None:
    """Parse explicit ISO dates/timestamps; never substitute the current clock."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    if text in {"", "NaT", "nan", "<NA>"}:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError as exc:
            raise ValueError(f"invalid age evidence date: {text!r}") from exc
