from __future__ import annotations

from collections import defaultdict
from statistics import mean

from fsffl.state.models import FrozenModel, LeagueState, Position

from .cardinal import NativeMarketMagnitudeObservation
from .cardinal_authority import FSFFL_CARDINAL_REFERENCE_SOURCE_ID


class PositionSourceConsistency(FrozenModel):
    """Diagnostic cross-source rank agreement for one player position.

    Percentiles are recomputed on the exact pairwise overlap universe so missing
    provider coverage cannot masquerade as a positional preference. This is
    research/diagnostic evidence only; it does not alter Cardinal Value.
    """

    source_id: str
    position: Position
    overlap_count: int
    mean_reference_percentile: float
    mean_source_percentile: float
    mean_signed_percentile_delta: float
    mean_absolute_percentile_delta: float


class PlayerSourceDisagreement(FrozenModel):
    player_id: str
    full_name: str
    position: Position
    source_id: str
    reference_value: float
    source_value: float
    reference_percentile: float
    source_percentile: float
    percentile_delta: float


class CardinalConsistencyAudit(FrozenModel):
    """Read-only audit of player Cardinal format and cross-source positional shape."""

    market_context_id: str
    reference_source_id: str = FSFFL_CARDINAL_REFERENCE_SOURCE_ID
    reference_format_key: str | None = None
    reference_player_count: int
    position_comparisons: tuple[PositionSourceConsistency, ...]
    largest_player_disagreements: tuple[PlayerSourceDisagreement, ...]
    model_version: str = "next3-cardinal-consistency-audit-v1"
    authority_effect: str = "diagnostic_only"


def _percentiles(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    if not ordered:
        return {}
    if len(ordered) == 1:
        return {ordered[0][0]: 0.5}
    result: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average_rank = (index + end - 1) / 2.0
        percentile = average_rank / (len(ordered) - 1)
        for offset in range(index, end):
            result[ordered[offset][0]] = percentile
        index = end
    return result


def build_cardinal_consistency_audit(
    league_state: LeagueState,
    observations: tuple[NativeMarketMagnitudeObservation, ...],
    *,
    market_context_id: str,
    reference_format_key: str | None = None,
    reference_source_id: str = FSFFL_CARDINAL_REFERENCE_SOURCE_ID,
    disagreement_limit: int = 24,
) -> CardinalConsistencyAudit:
    """Measure whether one reference market axis behaves differently by position.

    This deliberately compares ranks, not provider-native magnitudes, because the
    providers use different numeric scales. The key diagnostic is whether another
    same-context market systematically places QBs (or another position) higher or
    lower in the *overall dynasty market* than the Cardinal reference axis does.

    A missing reference source returns an empty diagnostic rather than failing the
    broader market runtime. Cardinal authority itself remains unavailable in that
    case; unrelated market evidence is not discarded because one provider is down.
    """

    if not market_context_id.strip():
        raise ValueError("market_context_id cannot be blank")
    if disagreement_limit < 0:
        raise ValueError("disagreement_limit cannot be negative")

    by_source: dict[str, dict[str, float]] = defaultdict(dict)
    reference_versions: set[str] = set()
    for row in observations:
        if row.market_context_id != market_context_id:
            continue
        by_source[row.source_id][row.asset_id] = row.value
        if row.source_id == reference_source_id and row.source_version:
            reference_versions.add(row.source_version)

    reference_values = by_source.get(reference_source_id, {})
    if not reference_values:
        return CardinalConsistencyAudit(
            market_context_id=market_context_id,
            reference_format_key=reference_format_key,
            reference_player_count=0,
            position_comparisons=(),
            largest_player_disagreements=(),
        )
    if reference_format_key is not None and reference_versions and reference_versions != {reference_format_key}:
        raise ValueError("reference source evidence mixes an unexpected format cohort")

    players = {player.player_id: player for player in league_state.players}
    comparisons: list[PositionSourceConsistency] = []
    disagreements: list[PlayerSourceDisagreement] = []

    for source_id, source_values in sorted(by_source.items()):
        if source_id == reference_source_id:
            continue
        shared_ids = sorted(set(reference_values).intersection(source_values).intersection(players))
        if len(shared_ids) < 2:
            continue
        reference_percentiles = _percentiles({asset_id: reference_values[asset_id] for asset_id in shared_ids})
        source_percentiles = _percentiles({asset_id: source_values[asset_id] for asset_id in shared_ids})
        grouped: dict[Position, list[tuple[float, float]]] = defaultdict(list)
        for asset_id in shared_ids:
            player = players[asset_id]
            reference_percentile = reference_percentiles[asset_id]
            source_percentile = source_percentiles[asset_id]
            grouped[player.position].append((reference_percentile, source_percentile))
            disagreements.append(
                PlayerSourceDisagreement(
                    player_id=asset_id,
                    full_name=player.full_name,
                    position=player.position,
                    source_id=source_id,
                    reference_value=reference_values[asset_id],
                    source_value=source_values[asset_id],
                    reference_percentile=reference_percentile,
                    source_percentile=source_percentile,
                    percentile_delta=source_percentile - reference_percentile,
                )
            )
        for position, rows in sorted(grouped.items(), key=lambda item: item[0].value):
            deltas = [source - reference for reference, source in rows]
            comparisons.append(
                PositionSourceConsistency(
                    source_id=source_id,
                    position=position,
                    overlap_count=len(rows),
                    mean_reference_percentile=mean(reference for reference, _ in rows),
                    mean_source_percentile=mean(source for _, source in rows),
                    mean_signed_percentile_delta=mean(deltas),
                    mean_absolute_percentile_delta=mean(abs(delta) for delta in deltas),
                )
            )

    disagreements.sort(
        key=lambda row: (-abs(row.percentile_delta), row.source_id, row.position.value, row.player_id)
    )
    return CardinalConsistencyAudit(
        market_context_id=market_context_id,
        reference_format_key=reference_format_key,
        reference_player_count=len(reference_values),
        position_comparisons=tuple(comparisons),
        largest_player_disagreements=tuple(disagreements[:disagreement_limit]),
    )
