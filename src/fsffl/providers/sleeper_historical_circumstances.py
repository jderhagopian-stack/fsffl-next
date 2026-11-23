"""Normalize supplied legacy production and Sleeper scores; no provider fetches.

Completion/availability receipts must be supplied separately. A week number or
season label never fabricates a completion date. Existing franchise crosswalks
and historical scoring vintages are retained; points are not recalculated.
"""
from collections import defaultdict
from collections.abc import Mapping, Sequence
from math import isfinite

from fsffl.behavioral.historical_circumstances import (
    HistoricalPlayerProduction, HistoricalProductionEvidence,
    HistoricalScoredMatchup, HistoricalResultsEvidence,
)
from fsffl.state.historical_coverage import HistoricalEvidenceReceipt
from fsffl.state.historical_season_lineage import HistoricalSeasonSource
from fsffl.state.historical_roster_context import _digest


def normalize_legacy_historical_production(rows: Sequence[Mapping], *,
        receipt: HistoricalEvidenceReceipt, scoring_rules_sha256: str) -> HistoricalProductionEvidence:
    """Read the retained league-scored player-season schema, not a universal value.

    Position is the source production season's position. Zero games do not prove
    poor quality; the downstream dossier keeps such players unobserved.
    """
    normalized = []
    for row in rows:
        year = row.get('season')
        if type(year) not in (str,int) or not str(year).isdigit() or int(year) != receipt.season.season:
            raise ValueError('production source season differs from receipt')
        if row.get('player_id') is None:
            raise ValueError('production player/position missing')
        points = row.get('fsffl_points'); games = row.get('games_with_stats')
        if isinstance(points, bool) or not isinstance(points, (int,float)) or not isfinite(points):
            raise ValueError('production points missing or invalid; no zero fallback')
        normalized.append(HistoricalPlayerProduction(str(row['player_id']),str(row['position']) if row.get('position') is not None else None,float(points),games))
    return HistoricalProductionEvidence(receipt,_digest(list(rows)),scoring_rules_sha256,tuple(normalized))


def normalize_sleeper_historical_results(rows: Sequence[Mapping], *, week: int,
        source: HistoricalSeasonSource, receipt: HistoricalEvidenceReceipt) -> HistoricalResultsEvidence:
    if receipt.season != source.season or source.provider_ref.provider != 'sleeper':
        raise ValueError('weekly results require matching admitted Sleeper season')
    mappings = {b.provider_roster_id:b.canonical_team_id for b in source.roster_bindings}
    grouped = defaultdict(list); incomplete = set(); seen = set()
    for row in rows:
        rid = str(row.get('roster_id'))
        if rid not in mappings or rid in seen:
            raise ValueError('unknown or duplicate weekly source roster')
        seen.add(rid)
        team_id = mappings[rid]
        score = row.get('custom_points') if row.get('custom_points') is not None else row.get('points')
        if row.get('matchup_id') is None or isinstance(score,bool) or not isinstance(score,(int,float)) or not isfinite(score):
            incomplete.add(team_id)
            continue
        grouped[str(row['matchup_id'])].append((team_id,float(score)))
    normalized = []
    for pair in grouped.values():
        if len(pair) != 2:
            incomplete.update(t for t,_ in pair)
            continue
        (a,ap),(b,bp) = pair
        normalized.extend((HistoricalScoredMatchup(a,b,ap,bp),HistoricalScoredMatchup(b,a,bp,ap)))
    incomplete.update(mappings[r] for r in mappings.keys()-seen)
    return HistoricalResultsEvidence(receipt,_digest(list(rows)),week,tuple(normalized),tuple(sorted(incomplete)))


def normalize_historical_season_window(rows, *, season, regular_season_end_week, season_end_week, source_sha256):
    """Calendar facts plus explicitly admitted league end weeks; no guessed format."""
    from datetime import date
    from fsffl.behavioral.historical_trade_context import HistoricalSeasonWindow
    if not 1<=regular_season_end_week<=season_end_week<=18:
        raise ValueError('explicit supported fantasy season end weeks required')
    weeks = defaultdict(list)
    for row in rows:
        if str(row.get('season'))==str(season) and row.get('game_type')=='REG':
            weeks[int(row['week'])].append(date.fromisoformat(row['gameday']))
    if not all(weeks.get(w) for w in (1,regular_season_end_week,season_end_week)):
        raise ValueError('season calendar boundaries unavailable')
    return HistoricalSeasonWindow(season=season,first_game_date=min(weeks[1]),
        regular_season_end_date=max(weeks[regular_season_end_week]),season_end_date=max(weeks[season_end_week]),
        source_sha256=source_sha256)
