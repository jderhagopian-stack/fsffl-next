from __future__ import annotations

from bisect import bisect_left
from itertools import combinations
from time import monotonic
from typing import Mapping

from fsffl.state.models import LeagueState, Position
from fsffl.team_utility.position_strength import LeagueRelativePositionStrength
from fsffl.value.cardinal_authority import FSFFLCardinalValueScore

from .runtime import UserRuntimeContext
from .trade_center_view import TradeAssetOption, TradeCenterBrowserView


_SKILL_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)
_MAX_DISCOVERY_PACKAGE_SIZE = 3
_PACKAGE_NEIGHBORHOOD_PER_SIZE = 3

PackageCatalog = dict[int, tuple[tuple[float, tuple[str, ...], tuple[TradeAssetOption, ...]], ...]]


class SearchCandidateCollection(list[dict[str, object]]):
    """List-compatible Search output with non-authoritative generation diagnostics."""

    def __init__(
        self,
        rows: list[dict[str, object]],
        *,
        diagnostics: dict[str, object],
    ) -> None:
        super().__init__(rows)
        self.diagnostics = diagnostics


def _player_position(league_state: LeagueState, option: TradeAssetOption) -> Position | None:
    if option.asset_kind != "player" or option.player_id is None:
        return None
    player = next((row for row in league_state.players if row.player_id == option.player_id), None)
    return player.position if player is not None else None


def _position_strengths(runtime: UserRuntimeContext) -> dict[str, dict[Position, LeagueRelativePositionStrength]]:
    """Consume already-published league-relative position strength evidence.

    Search does not rebuild this derived truth; it only consumes the common
    Analytics/Simulation position-strength rows for exploration context.
    """

    simulation = runtime.simulation_analytics
    if simulation is None:
        return {}
    result: dict[str, dict[Position, LeagueRelativePositionStrength]] = {}
    for view in simulation.team_views:
        for row in view.position_strengths:
            if row.position in _SKILL_POSITIONS:
                result.setdefault(view.team_id, {})[row.position] = row
    return result


def _asset_value(option: TradeAssetOption, cardinal: Mapping[str, FSFFLCardinalValueScore]) -> float | None:
    asset_id = option.player_id or option.pick_id
    row = cardinal.get(asset_id or "")
    return row.score if row is not None else None


def _asset_payload(option: TradeAssetOption, value: float) -> dict[str, object]:
    """Publish existing canonical asset metadata without creating new Search truth."""

    return {
        "asset_ref": option.asset_ref,
        "label": option.label,
        "asset_kind": option.asset_kind,
        "detail": option.detail,
        "age_years": option.age_years,
        "roster_slot": option.roster_slot.value if option.roster_slot is not None else None,
        "fsffl_value": value,
    }


def _relative_market_gap(receive_value: float, send_total: float) -> float:
    denominator = max(abs(receive_value), abs(send_total))
    return abs(receive_value - send_total) / denominator if denominator > 0.0 else 0.0


def _weakest_receive_fit(
    *,
    league_state: LeagueState,
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]],
    team_id: str,
    send_assets: tuple[TradeAssetOption, ...],
) -> LeagueRelativePositionStrength | None:
    positions = [
        position
        for option in send_assets
        if (position := _player_position(league_state, option)) is not None
    ]
    rows = [strengths.get(team_id, {}).get(position) for position in positions]
    resolved = [row for row in rows if row is not None]
    if not resolved:
        return None
    return min(
        resolved,
        key=lambda row: (
            row.strength_index if row.strength_index is not None else 100.0,
            -row.league_rank,
            row.position.value,
        ),
    )


def _candidate(
    *,
    league_state: LeagueState,
    focal_team_id: str,
    counterparty_team_id: str,
    counterparty_name: str,
    send_assets: tuple[TradeAssetOption, ...],
    receive_asset: TradeAssetOption,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]],
) -> dict[str, object] | None:
    receive_value = _asset_value(receive_asset, cardinal)
    send_values = tuple(_asset_value(option, cardinal) for option in send_assets)
    if receive_value is None or any(value is None for value in send_values):
        return None
    resolved_send_values = tuple(float(value) for value in send_values if value is not None)
    send_total = sum(resolved_send_values)
    target_position = _player_position(league_state, receive_asset)
    focal_strength = strengths.get(focal_team_id, {}).get(target_position) if target_position is not None else None
    counterparty_fit = _weakest_receive_fit(
        league_state=league_state,
        strengths=strengths,
        team_id=counterparty_team_id,
        send_assets=send_assets,
    )
    shape = {1: "one_for_one", 2: "two_for_one", 3: "three_for_one"}.get(
        len(send_assets), f"{len(send_assets)}_for_one"
    )
    context: list[str] = []
    if focal_strength is not None:
        strength_text = f"{focal_strength.strength_index:.0f}" if focal_strength.strength_index is not None else "unavailable"
        context.append(
            f"Target addresses {target_position.value}: strength index {strength_text} "
            f"(league average 100), rank #{focal_strength.league_rank}."
        )
    if counterparty_fit is not None:
        strength_text = f"{counterparty_fit.strength_index:.0f}" if counterparty_fit.strength_index is not None else "unavailable"
        context.append(
            f"Assets sent include {counterparty_fit.position.value}, where the other team has "
            f"strength index {strength_text} and rank #{counterparty_fit.league_rank}."
        )
    if len(send_assets) > 1:
        context.append(
            f"Consolidation structure: {len(send_assets)} focal assets for one target. Search does not "
            "award a consolidation premium; NEXT-5 Decision owns package economics."
        )
    return {
        "kind": "trade",
        "discovery_status": "structurally_valid",
        "action_authority": "diagnostic_only",
        "evidence_completeness": "partial",
        "counterparty_team_id": counterparty_team_id,
        "counterparty_name": counterparty_name,
        "send": [
            _asset_payload(option, value)
            for option, value in zip(send_assets, resolved_send_values, strict=True)
        ],
        "receive": [_asset_payload(receive_asset, receive_value)],
        "package_shape": shape,
        "target_position": target_position.value if target_position is not None else None,
        "target_fsffl_value": float(receive_value),
        "focal_position_strength_rank": focal_strength.league_rank if focal_strength is not None else None,
        "focal_position_strength_index": focal_strength.strength_index if focal_strength is not None else None,
        "counterparty_receive_position_rank": counterparty_fit.league_rank if counterparty_fit is not None else None,
        "counterparty_receive_position_strength_index": counterparty_fit.strength_index if counterparty_fit is not None else None,
        "search_distance": abs(receive_value - send_total),
        "market_gap_ratio": _relative_market_gap(receive_value, send_total),
        "reasons": ["unknown_acceptance", "materiality_not_evaluated"],
        "search_context": context,
        "bilateral_decision_evaluated": False,
        "explanation": (
            "Broad structural trade search. Cardinal Value is one market-plausibility coordinate, "
            "not the definition of the best opportunity; Decision and acceptance evidence remain incomplete."
        ),
    }


def _build_package_catalog(
    focal_assets: tuple[TradeAssetOption, ...],
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    *,
    required_asset_ref: str | None = None,
    minimum_size: int = 1,
) -> PackageCatalog:
    """Enumerate only strategically admitted package ingredients.

    Search may constrain the focal asset set before package construction using
    already-governed roster/position evidence. Cardinal Value is then used only
    to build a bounded economic neighborhood inside that admitted universe.
    """

    valued_focal = tuple(
        (asset, float(value))
        for asset in focal_assets
        if (value := _asset_value(asset, cardinal)) is not None
    )
    if required_asset_ref and all(
        asset.asset_ref != required_asset_ref for asset, _ in valued_focal
    ):
        return {}
    catalog: PackageCatalog = {}
    max_size = min(_MAX_DISCOVERY_PACKAGE_SIZE, len(valued_focal))
    for size in range(max(1, minimum_size), max_size + 1):
        entries: list[tuple[float, tuple[str, ...], tuple[TradeAssetOption, ...]]] = []
        for package in combinations(valued_focal, size):
            assets = tuple(asset for asset, _ in package)
            if required_asset_ref and all(
                asset.asset_ref != required_asset_ref for asset in assets
            ):
                continue
            total = sum(value for _, value in package)
            refs = tuple(sorted(asset.asset_ref for asset in assets))
            entries.append((total, refs, assets))
        entries.sort(key=lambda item: (item[0], item[1]))
        catalog[size] = tuple(entries)
    return catalog


def _nearest_packages(
    catalog: PackageCatalog,
    *,
    size: int,
    target_value: float,
    limit: int = _PACKAGE_NEIGHBORHOOD_PER_SIZE,
) -> tuple[tuple[TradeAssetOption, ...], ...]:
    """Return a bounded Cardinal neighborhood without creating a package score.

    Search deliberately keeps several nearby structures so the single closest
    additive package cannot monopolize the path before Decision-owned economics
    and bilateral screening run. The neighborhood size is product compute policy,
    not Value or Decision authority.
    """

    entries = catalog.get(size) or ()
    if not entries or limit <= 0:
        return ()
    totals = [item[0] for item in entries]
    insertion = bisect_left(totals, target_value)
    radius = max(limit * 2, 4)
    start = max(0, insertion - radius)
    end = min(len(entries), insertion + radius + 1)
    ordered = sorted(
        entries[start:end],
        key=lambda item: (abs(item[0] - target_value), item[1]),
    )
    return tuple(item[2] for item in ordered[:limit])


def _nearest_packages_for_target(
    *,
    league_state: LeagueState,
    focal_team_id: str,
    counterparty_team_id: str,
    counterparty_name: str,
    package_catalog: PackageCatalog,
    target: TradeAssetOption,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]],
) -> tuple[dict[str, object], ...]:
    """Generate a bounded structural neighborhood for every target.

    Keep the nearest Cardinal package at each supported size instead of allowing
    the best single asset to veto all package complexity. This expands premium-target
    access without inventing a consolidation coefficient or acceptance rule.
    """

    target_value = _asset_value(target, cardinal)
    if target_value is None:
        return ()
    rows: list[dict[str, object]] = []
    for size in sorted(package_catalog):
        packages = _nearest_packages(
            package_catalog,
            size=size,
            target_value=float(target_value),
        )
        for variant_rank, package in enumerate(packages, start=1):
            row = _candidate(
                league_state=league_state,
                focal_team_id=focal_team_id,
                counterparty_team_id=counterparty_team_id,
                counterparty_name=counterparty_name,
                send_assets=package,
                receive_asset=target,
                cardinal=cardinal,
                strengths=strengths,
            )
            if row is not None:
                row["package_variant_rank"] = variant_rank
                row["search_context"] = [
                    *(row.get("search_context") or []),
                    f"Search retained bounded governed {size}-asset market-neighborhood variant "
                    f"#{variant_rank} for this target. Package size and neighborhood rank are "
                    "exploratory product policy; Decision owns whether the structure is actually good.",
                ]
                rows.append(row)
    return tuple(rows)


def _strength(row: dict[str, object], key: str) -> float:
    value = row.get(key)
    return float(value) if value is not None else float("inf")


def _target_value(row: dict[str, object]) -> float:
    value = row.get("target_fsffl_value")
    return float(value) if value is not None else float("-inf")


def _multi_lane_search_order(candidates: list[dict[str, object]]) -> list[dict[str, object]]:
    """Interleave distinct Search lenses before the workspace truncates candidates.

    The first row remains the closest market match. Subsequent rows are admitted in
    round-robin order from market fit, premium target value, focal roster need,
    counterparty fit, and package complexity. No metrics are blended into a score.
    """

    if not candidates:
        return []
    indices = range(len(candidates))
    lanes = (
        sorted(indices, key=lambda i: (float(candidates[i]["market_gap_ratio"]), float(candidates[i]["search_distance"]), i)),
        sorted(indices, key=lambda i: (-_target_value(candidates[i]), float(candidates[i]["market_gap_ratio"]), i)),
        sorted(indices, key=lambda i: (_strength(candidates[i], "focal_position_strength_index"), float(candidates[i]["market_gap_ratio"]), i)),
        sorted(indices, key=lambda i: (_strength(candidates[i], "counterparty_receive_position_strength_index"), float(candidates[i]["market_gap_ratio"]), i)),
        sorted(indices, key=lambda i: (-len(candidates[i].get("send") or []), float(candidates[i]["market_gap_ratio"]), i)),
    )
    ordered: list[int] = []
    seen: set[int] = set()
    cursors = [0] * len(lanes)
    while len(ordered) < len(candidates):
        progressed = False
        for lane_index, lane in enumerate(lanes):
            while cursors[lane_index] < len(lane) and lane[cursors[lane_index]] in seen:
                cursors[lane_index] += 1
            if cursors[lane_index] >= len(lane):
                continue
            candidate_index = lane[cursors[lane_index]]
            cursors[lane_index] += 1
            seen.add(candidate_index)
            ordered.append(candidate_index)
            progressed = True
        if not progressed:
            break
    return [candidates[index] for index in ordered]


def _target_path_family_key(row: dict[str, object]) -> tuple[str, tuple[str, ...]]:
    return (
        str(row.get("counterparty_team_id") or ""),
        tuple(
            sorted(
                str(item.get("asset_ref") or "")
                for item in (row.get("receive") or [])
                if isinstance(item, dict) and item.get("asset_ref")
            )
        ),
    )


def _family_first_search_order(
    candidates: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Preserve target/path diversity before the workspace candidate bound.

    Multi-lane Search still determines the first appearance and within-family
    ordering. This second pass changes only admission order: every distinct
    target/counterparty path family gets one row before any family gets a second
    package variant. It prevents package-neighborhood repetition from consuming
    the bounded workspace before Opportunity/Decision screening.
    """

    ordered = _multi_lane_search_order(candidates)
    families: dict[
        tuple[str, tuple[str, ...]],
        list[dict[str, object]],
    ] = {}
    family_order: list[tuple[str, tuple[str, ...]]] = []
    for row in ordered:
        key = _target_path_family_key(row)
        if key not in families:
            families[key] = []
            family_order.append(key)
        families[key].append(row)

    result: list[dict[str, object]] = []
    depth = 0
    while len(result) < len(ordered):
        progressed = False
        for key in family_order:
            rows = families[key]
            if depth >= len(rows):
                continue
            result.append(rows[depth])
            progressed = True
        if not progressed:
            break
        depth += 1
    return result


def _fragility_positions(
    runtime: UserRuntimeContext,
    team_id: str,
) -> tuple[Position, ...]:
    simulation = runtime.simulation_analytics
    league_state = runtime.league_state
    if simulation is None or league_state is None:
        return ()
    view = next((row for row in simulation.team_views if row.team_id == team_id), None)
    resilience = (
        view.utility.roster_resilience
        if view is not None
        and view.utility is not None
        and view.utility.roster_resilience is not None
        else None
    )
    if resilience is None:
        return ()
    players = {player.player_id: player for player in league_state.players}
    result: list[Position] = []
    for player_id in resilience.largest_single_player_lineup_drop_player_ids:
        player = players.get(player_id)
        if player is not None and player.position in _SKILL_POSITIONS and player.position not in result:
            result.append(player.position)
    return tuple(result)


def actionable_need_positions(
    runtime: UserRuntimeContext,
    team_id: str,
    *,
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]] | None = None,
) -> tuple[Position, ...]:
    """Return transparent roster-need hypotheses from existing Team Utility evidence.

    Positions in the bottom half of league-relative optimized starter production
    are admitted as needs. A current largest-fragility driver position is also
    admitted. If governed strength evidence exists but no position is below the
    median, the single weakest position remains an explicit exploration hypothesis.
    No cross-dimension score is created.
    """

    resolved = strengths if strengths is not None else _position_strengths(runtime)
    rows = list(resolved.get(team_id, {}).values())
    ordered = sorted(
        rows,
        key=lambda row: (
            row.strength_index if row.strength_index is not None else float("inf"),
            -row.league_rank,
            row.position.value,
        ),
    )
    result: list[Position] = [
        row.position
        for row in ordered
        if row.league_rank > max(1, row.team_count // 2)
    ]
    if not result and ordered:
        result.append(ordered[0].position)
    for position in _fragility_positions(runtime, team_id):
        if position not in result:
            result.append(position)
    return tuple(result)


def supply_positions(
    runtime: UserRuntimeContext,
    team_id: str,
    *,
    strengths: dict[str, dict[Position, LeagueRelativePositionStrength]] | None = None,
) -> tuple[Position, ...]:
    """Return positions where a team has top-half governed starter strength."""

    resolved = strengths if strengths is not None else _position_strengths(runtime)
    rows = list(resolved.get(team_id, {}).values())
    ordered = sorted(
        rows,
        key=lambda row: (
            row.league_rank,
            -(row.strength_index if row.strength_index is not None else 0.0),
            row.position.value,
        ),
    )
    result = [
        row.position
        for row in ordered
        if row.league_rank <= max(1, row.team_count // 2)
    ]
    if not result and ordered:
        result.append(ordered[0].position)
    return tuple(result)


def _complementary_send_assets(
    league_state: LeagueState,
    focal_assets: tuple[TradeAssetOption, ...],
    *,
    counterparty_needs: tuple[Position, ...],
) -> tuple[TradeAssetOption, ...]:
    """Admit picks plus focal players that address a governed counterparty need."""

    if not counterparty_needs:
        return focal_assets
    admitted = tuple(
        asset
        for asset in focal_assets
        if asset.asset_kind == "pick"
        or _player_position(league_state, asset) in counterparty_needs
    )
    return admitted


def build_scoped_trade_candidates(
    runtime: UserRuntimeContext,
    browser: TradeCenterBrowserView,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
    *,
    counterparty_team_ids: frozenset[str] | None = None,
    target_asset_refs: frozenset[str] | None = None,
    target_positions: frozenset[Position] | None = None,
    require_counterparty_supply: bool = False,
    required_send_asset_ref: str | None = None,
    required_counterparty_need_position: Position | None = None,
    minimum_send_count: int = 1,
    scope_label: str = "automatic_improve",
) -> SearchCandidateCollection:
    """Generate packages only after strategic/counterparty admission.

    This is Search/Optimization orchestration over existing State, Team Utility and
    Value evidence. Need/supply categories decide which neighborhoods are worth
    constructing; Cardinal Value only chooses bounded package neighbors *inside*
    that strategically admitted universe.
    """

    started = monotonic()
    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None or focal_team_id is None:
        return SearchCandidateCollection([], diagnostics={})

    strengths = _position_strengths(runtime)
    focal_needs = actionable_need_positions(
        runtime,
        focal_team_id,
        strengths=strengths,
    )
    effective_target_positions = (
        target_positions
        if target_positions is not None
        else frozenset(focal_needs or _SKILL_POSITIONS)
    )
    admission_finished = monotonic()

    candidates: list[dict[str, object]] = []
    seen: set[tuple[str, tuple[str, ...], str]] = set()
    raw_packages_generated = 0
    exact_duplicates_removed = 0
    counterparties_considered = 0
    counterparties_admitted = 0
    targets_considered = 0
    targets_admitted = 0
    send_assets_considered = 0
    send_assets_admitted = 0
    rejection_reasons = {
        "counterparty_not_selected": 0,
        "counterparty_lacks_required_need": 0,
        "target_not_selected": 0,
        "target_not_focal_need": 0,
        "target_not_counterparty_supply": 0,
        "no_complementary_send_assets": 0,
    }

    for counterparty in browser.counterparties:
        counterparties_considered += 1
        if (
            counterparty_team_ids is not None
            and counterparty.team_id not in counterparty_team_ids
        ):
            rejection_reasons["counterparty_not_selected"] += 1
            continue
        counterparty_needs = actionable_need_positions(
            runtime,
            counterparty.team_id,
            strengths=strengths,
        )
        counterparty_supply = supply_positions(
            runtime,
            counterparty.team_id,
            strengths=strengths,
        )
        if (
            required_counterparty_need_position is not None
            and counterparty_needs
            and required_counterparty_need_position not in counterparty_needs
        ):
            rejection_reasons["counterparty_lacks_required_need"] += 1
            continue

        admitted_focal_assets = _complementary_send_assets(
            league_state,
            browser.focal_team.assets,
            counterparty_needs=counterparty_needs,
        )
        send_assets_considered += len(browser.focal_team.assets)
        send_assets_admitted += len(admitted_focal_assets)
        package_catalog = _build_package_catalog(
            admitted_focal_assets,
            cardinal,
            required_asset_ref=required_send_asset_ref,
            minimum_size=minimum_send_count,
        )
        if not package_catalog:
            rejection_reasons["no_complementary_send_assets"] += 1
            continue

        admitted_targets: list[TradeAssetOption] = []
        for target in counterparty.assets:
            if target.asset_kind != "player":
                continue
            targets_considered += 1
            if target_asset_refs is not None and target.asset_ref not in target_asset_refs:
                rejection_reasons["target_not_selected"] += 1
                continue
            position = _player_position(league_state, target)
            if (
                target_positions is not None
                and position not in effective_target_positions
            ):
                rejection_reasons["target_not_focal_need"] += 1
                continue
            if (
                target_positions is None
                and focal_needs
                and position not in effective_target_positions
            ):
                rejection_reasons["target_not_focal_need"] += 1
                continue
            if (
                require_counterparty_supply
                and counterparty_supply
                and position not in counterparty_supply
            ):
                rejection_reasons["target_not_counterparty_supply"] += 1
                continue
            admitted_targets.append(target)

        if not admitted_targets:
            continue
        counterparties_admitted += 1
        targets_admitted += len(admitted_targets)

        for target in admitted_targets:
            for row in _nearest_packages_for_target(
                league_state=league_state,
                focal_team_id=focal_team_id,
                counterparty_team_id=counterparty.team_id,
                counterparty_name=counterparty.display_name,
                package_catalog=package_catalog,
                target=target,
                cardinal=cardinal,
                strengths=strengths,
            ):
                raw_packages_generated += 1
                key = (
                    counterparty.team_id,
                    tuple(sorted(str(item["asset_ref"]) for item in row["send"])),
                    str(row["receive"][0]["asset_ref"]),
                )
                if key in seen:
                    exact_duplicates_removed += 1
                    continue
                seen.add(key)
                row["search_context"] = [
                    *list(row.get("search_context") or []),
                    (
                        f"Candidate neighborhood admitted before package generation by "
                        f"{scope_label}: target/counterparty fit came from governed roster "
                        "and position-strength evidence; Cardinal Value only bounded package cost."
                    ),
                ]
                candidates.append(row)

    package_generation_finished = monotonic()
    ordered = _family_first_search_order(candidates)
    completed = monotonic()
    return SearchCandidateCollection(
        ordered,
        diagnostics={
            "scope_label": scope_label,
            "focal_need_positions": tuple(position.value for position in focal_needs),
            "counterparties_considered": counterparties_considered,
            "counterparties_admitted_pre_package": counterparties_admitted,
            "targets_considered": targets_considered,
            "targets_admitted_pre_package": targets_admitted,
            "send_assets_considered": send_assets_considered,
            "send_assets_admitted_for_counterparty_need": send_assets_admitted,
            "raw_packages_generated_pre_dedup": raw_packages_generated,
            "packages_removed_exact_duplicate": exact_duplicates_removed,
            "candidate_rows_after_exact_dedup": len(ordered),
            "admission_rejection_reasons": rejection_reasons,
            "timing_ms": {
                "strategic_admission_setup": round(
                    (admission_finished - started) * 1000.0,
                    3,
                ),
                "package_generation": round(
                    (package_generation_finished - admission_finished) * 1000.0,
                    3,
                ),
                "ordering": round(
                    (completed - package_generation_finished) * 1000.0,
                    3,
                ),
                "total": round((completed - started) * 1000.0, 3),
            },
        },
    )


def build_roster_aware_trade_candidates(
    runtime: UserRuntimeContext,
    browser: TradeCenterBrowserView,
    cardinal: Mapping[str, FSFFLCardinalValueScore],
) -> SearchCandidateCollection:
    """Build automatic discovery from actionable needs and complementary rosters."""

    return build_scoped_trade_candidates(
        runtime,
        browser,
        cardinal,
        require_counterparty_supply=True,
        scope_label="automatic_improve",
    )
