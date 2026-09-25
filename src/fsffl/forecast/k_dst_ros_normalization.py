from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime

from fsffl.state.models import (
    FrozenModel,
    Player,
    Position,
    Provenance,
    ProviderRef,
    canonical_nfl_team,
)

from .late_start_snapshot import LateStartProviderEvidence, ros_subject_key
from .models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
    NflTeamUnitForecastSubject,
    TeamUnitForecastObservation,
)


class LateStartNormalizedEvidence(FrozenModel):
    kicker_observations: tuple[ForecastObservation, ...] = ()
    dst_observations: tuple[TeamUnitForecastObservation, ...] = ()


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return "".join(re.findall(r"[a-z0-9]+", ascii_text.lower()))


def _kicker_indexes(
    players: tuple[Player, ...],
) -> tuple[
    dict[tuple[str, str], list[Player]],
    dict[str, list[Player]],
]:
    exact: dict[tuple[str, str], list[Player]] = {}
    loose: dict[str, list[Player]] = {}
    for player in players:
        if player.position != Position.K:
            continue
        name = _normalize_name(player.full_name)
        team = canonical_nfl_team(player.nfl_team) if player.nfl_team else ""
        exact.setdefault((name, team), []).append(player)
        loose.setdefault(name, []).append(player)
    return exact, loose


def _kicker_metric(stat: str) -> ForecastMetric | None:
    try:
        metric = ForecastMetric(stat)
    except ValueError:
        return None
    return metric if metric.value.startswith(("fg_", "xp_")) else None


def _dst_metric(stat: str) -> ForecastMetric | None:
    try:
        metric = ForecastMetric(stat)
    except ValueError:
        return None
    return metric if metric.value.startswith("dst_") else None


def normalize_late_start_provider_evidence(
    evidence: LateStartProviderEvidence,
    *,
    players: tuple[Player, ...],
    season: int,
    period_start: datetime,
    period_end: datetime,
    evaluation_as_of: datetime,
) -> LateStartNormalizedEvidence:
    """Normalize accepted K/DST ROS rows without creating fantasy-point authority."""

    if season != 2026:
        raise ValueError("late-start K/DST normalization is authorized only for 2026")
    for name, value in (
        ("period_start", period_start),
        ("period_end", period_end),
        ("evaluation_as_of", evaluation_as_of),
    ):
        if value.tzinfo is None:
            raise ValueError(f"{name} must be timezone-aware")
    period_start = period_start.astimezone(UTC)
    period_end = period_end.astimezone(UTC)
    evaluation_as_of = evaluation_as_of.astimezone(UTC)
    if period_end <= period_start:
        raise ValueError("ROS period_end must follow period_start")
    if evidence.captured_at > evaluation_as_of:
        raise ValueError("provider acquisition cannot postdate evaluation_as_of")

    exact, loose = _kicker_indexes(players)
    accepted = set(evidence.accepted_subject_keys)
    effective_at = evidence.provider_effective_at or evidence.captured_at
    k_output: list[ForecastObservation] = []
    dst_output: list[TeamUnitForecastObservation] = []

    for row in evidence.raw_rows:
        if ros_subject_key(row) not in accepted:
            continue
        provenance = Provenance(
            source=evidence.provider,
            retrieved_at=evidence.captured_at,
            effective_at=effective_at,
            provider_ref=ProviderRef(
                provider=evidence.provider,
                external_id=row.external_id,
            ),
            source_version=evidence.source_version,
        )

        if row.position == Position.K:
            name = _normalize_name(row.subject_name)
            team = canonical_nfl_team(row.nfl_team)
            matches = exact.get((name, team), [])
            if len(matches) == 1:
                player = matches[0]
            elif len(matches) > 1:
                continue
            else:
                loose_matches = loose.get(name, [])
                if len(loose_matches) != 1:
                    continue
                player = loose_matches[0]
            for stat, value in row.stats:
                metric = _kicker_metric(stat)
                if metric is None:
                    continue
                k_output.append(
                    ForecastObservation(
                        player_id=player.player_id,
                        position=Position.K,
                        horizon=ForecastHorizon.REST_OF_SEASON,
                        metric=metric,
                        period_start=period_start,
                        period_end=period_end,
                        distribution=ForecastDistribution(mean=float(value), stddev=0.0),
                        source=evidence.provider,
                        model_version=evidence.source_version,
                        as_of=evaluation_as_of,
                        provenance=provenance,
                    )
                )
        elif row.position == Position.DST:
            subject = NflTeamUnitForecastSubject(
                season=season,
                nfl_team=row.nfl_team,
            )
            for stat, value in row.stats:
                metric = _dst_metric(stat)
                if metric is None:
                    continue
                dst_output.append(
                    TeamUnitForecastObservation(
                        subject=subject,
                        horizon=ForecastHorizon.REST_OF_SEASON,
                        metric=metric,
                        period_start=period_start,
                        period_end=period_end,
                        distribution=ForecastDistribution(mean=float(value), stddev=0.0),
                        source=evidence.provider,
                        model_version=evidence.source_version,
                        as_of=evaluation_as_of,
                        provenance=provenance,
                    )
                )

    return LateStartNormalizedEvidence(
        kicker_observations=tuple(
            sorted(k_output, key=lambda item: (item.player_id, item.metric.value))
        ),
        dst_observations=tuple(
            sorted(
                dst_output,
                key=lambda item: (
                    item.subject.nfl_team,
                    item.metric.value,
                ),
            )
        ),
    )
