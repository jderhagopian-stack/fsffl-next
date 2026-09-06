from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fsffl.state.models import LeagueState, RosterSlot

from .calibration import CalibrationObservation
from .cardinal import NativeMarketMagnitudeObservation, preserve_native_market_magnitudes
from .market import MarketEvidenceKind, MarketObservation, estimate_market_price
from .models import MarketPriceEstimate, ValueAssetKind, ValueScale
from .source_batch import build_market_calibration_panel_batch
from .source_catalog import next3_market_source_registry_v1
from .sources import (
    normalize_dynastydealer_values,
    normalize_fantasycalc_values,
    normalize_statsguy_rankings,
)

DYNASTYDEALER_URL = "https://www.dynastydealer.com/api/player-values"
FANTASYCALC_URL = "https://api.fantasycalc.com/values/current"
STATSGUY_URL = "https://api.statsguyfantasy.com/api/v1/rankings"
MARKET_PERCENTILE_SCALE = ValueScale(
    scale_id="dynasty-market-percentile",
    version="next3-v1",
    unit_label="market percentile",
)


@dataclass(frozen=True)
class CurrentMarketValueRuntimeResult:
    league_state_id: str
    estimates: tuple[MarketPriceEstimate, ...]
    successful_source_ids: tuple[str, ...]
    failed_sources: tuple[str, ...]
    errors_by_source_id: dict[str, str]
    roster_player_count: int
    valued_roster_player_count: int
    market_context_id: str
    native_magnitude_observations: tuple[NativeMarketMagnitudeObservation, ...] = ()
    model_version: str = "next3-current-market-runtime-v1"

    @property
    def coverage(self) -> float:
        if self.roster_player_count == 0:
            return 0.0
        return self.valued_roster_player_count / self.roster_player_count


def _download_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "fsffl-next-private-beta/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - governed fixed source URLs
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset)


def _sleeper_crosswalk(league_state: LeagueState) -> dict[str, str]:
    crosswalk: dict[str, str] = {}
    for player in league_state.players:
        for ref in player.provider_refs:
            if ref.provider == "sleeper":
                prior = crosswalk.get(ref.external_id)
                if prior is not None and prior != player.player_id:
                    raise ValueError(f"conflicting Sleeper identity for {ref.external_id}")
                crosswalk[ref.external_id] = player.player_id
    return crosswalk


def _format_inputs(league_state: LeagueState) -> tuple[int, int, float, str]:
    lineup = league_state.league.rules.lineup
    superflex = any(item.slot == RosterSlot.SUPERFLEX and item.count > 0 for item in lineup)
    num_qbs = 2 if superflex else 1
    ppr = 0.0
    for rule in league_state.league.rules.scoring:
        if rule.stat.strip().lower() in {"rec", "reception", "receptions"}:
            ppr = float(rule.points)
            break
    # Provider APIs support the common 0/0.5/1 PPR cohorts. Fail closed rather
    # than silently snapping unusual league scoring to a neighboring format.
    if ppr not in {0.0, 0.5, 1.0}:
        raise ValueError(f"unsupported live market PPR cohort: {ppr}")
    context = f"dynasty:{league_state.league.rules.team_count}t:{'sf' if superflex else '1qb'}:{ppr:g}ppr"
    return num_qbs, league_state.league.rules.team_count, ppr, context


def _latest_source_values(
    observations: tuple[CalibrationObservation, ...],
) -> dict[str, dict[str, float]]:
    latest: dict[tuple[str, str], CalibrationObservation] = {}
    for row in observations:
        if row.asset_id is None or row.metric != "market_value":
            continue
        key = (row.source_id, row.asset_id)
        prior = latest.get(key)
        if prior is None or row.observed_at > prior.observed_at:
            latest[key] = row
    by_source: dict[str, dict[str, float]] = defaultdict(dict)
    for (source_id, asset_id), row in latest.items():
        by_source[source_id][asset_id] = row.value
    return by_source


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
        average_zero_based_rank = ((index + end - 1) / 2.0)
        percentile = average_zero_based_rank / (len(ordered) - 1)
        for offset in range(index, end):
            result[ordered[offset][0]] = percentile
        index = end
    return result


def build_current_market_values(league_state: LeagueState) -> CurrentMarketValueRuntimeResult:
    """Acquire current governed NEXT-3 market evidence and build typed estimates.

    Provider-native numeric scales are retained as typed challenger evidence and
    then converted to within-source percentiles for the current authoritative
    market baseline. The governed source registry collapses providers that share
    one evidence-family root so correlated feeds cannot double-vote.
    """

    sleeper_crosswalk = _sleeper_crosswalk(league_state)
    if not sleeper_crosswalk:
        raise ValueError("current LeagueState has no Sleeper player identity crosswalk")
    num_qbs, num_teams, ppr, context = _format_inputs(league_state)
    acquisition_time = datetime.now(UTC)

    fantasycalc_url = f"{FANTASYCALC_URL}?{urlencode({'isDynasty': 'true', 'numQbs': num_qbs, 'numTeams': num_teams, 'ppr': ppr})}"
    statsguy_format = "sf_dynasty" if num_qbs == 2 else "non_sf_dynasty"
    statsguy_url = f"{STATSGUY_URL}?{urlencode({'format': statsguy_format, 'limit': 1000})}"

    def load_dynastydealer():
        return normalize_dynastydealer_values(
            _download_text(DYNASTYDEALER_URL),
            asset_id_by_sleeper_id=sleeper_crosswalk,
            format_context_id=context,
            provenance_uri=DYNASTYDEALER_URL,
        ).observations

    def load_fantasycalc():
        return normalize_fantasycalc_values(
            _download_text(fantasycalc_url),
            observed_at=acquisition_time,
            asset_id_by_sleeper_id=sleeper_crosswalk,
            format_context_id=context,
            provenance_uri=fantasycalc_url,
        ).observations

    def load_statsguy():
        return normalize_statsguy_rankings(
            _download_text(statsguy_url),
            asset_id_by_sleeper_id=sleeper_crosswalk,
            format_context_id=context,
            provenance_uri=statsguy_url,
        ).observations

    batch = build_market_calibration_panel_batch(
        {
            "dynastydealer_market_values": load_dynastydealer,
            "fantasycalc_market_values": load_fantasycalc,
            "statsguy_market_values": load_statsguy,
        },
        as_of=acquisition_time,
        panel_version="next3-live-market-panel-v1",
        max_workers=3,
    )
    if not batch.panel.observations:
        raise RuntimeError("current governed market sources produced no usable observations")

    native_magnitude_observations = preserve_native_market_magnitudes(batch.panel.observations)

    market_observations: list[MarketObservation] = []
    for source_id, values in _latest_source_values(batch.panel.observations).items():
        percentile_values = _percentiles(values)
        latest_at = max(
            row.observed_at
            for row in batch.panel.observations
            if row.source_id == source_id and row.asset_id in percentile_values
        )
        for asset_id, value in percentile_values.items():
            market_observations.append(
                MarketObservation(
                    asset_id=asset_id,
                    asset_kind=ValueAssetKind.PLAYER,
                    source=source_id,
                    evidence_kind=MarketEvidenceKind.MARKET_INDEX,
                    observed_at=min(latest_at, acquisition_time),
                    value=value,
                    scale=MARKET_PERCENTILE_SCALE,
                )
            )

    observations_tuple = tuple(market_observations)
    registry = next3_market_source_registry_v1()
    estimates: list[MarketPriceEstimate] = []
    for asset_id in sorted({row.asset_id for row in observations_tuple}):
        try:
            estimates.append(
                estimate_market_price(
                    observations_tuple,
                    asset_id=asset_id,
                    asset_kind=ValueAssetKind.PLAYER,
                    scale=MARKET_PERCENTILE_SCALE,
                    as_of=acquisition_time,
                    market_context_id=context,
                    model_version="next3-current-market-runtime-v1",
                    minimum_sources=1,
                    source_registry=registry,
                )
            )
        except ValueError:
            continue

    roster_player_ids = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    valued = roster_player_ids.intersection({estimate.asset_id for estimate in estimates})
    failures = list(batch.failed_source_ids)
    errors = dict(batch.errors_by_source_id)
    # DynastyProcess requires an explicit FantasyPros->canonical crosswalk that
    # current Sleeper State does not presently carry. Surface that absence rather
    # than name-matching or silently treating the source as empty evidence.
    failures.append("dynastyprocess_market_values")
    errors["dynastyprocess_market_values"] = "IdentityCrosswalkUnavailable: current State lacks explicit FantasyPros ids"

    return CurrentMarketValueRuntimeResult(
        league_state_id=league_state.state_id,
        estimates=tuple(estimates),
        successful_source_ids=batch.completed_source_ids,
        failed_sources=tuple(sorted(set(failures))),
        errors_by_source_id=errors,
        roster_player_count=len(roster_player_ids),
        valued_roster_player_count=len(valued),
        market_context_id=context,
        native_magnitude_observations=native_magnitude_observations,
    )
