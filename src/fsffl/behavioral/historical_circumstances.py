"""Descriptive historical circumstances, independent of preference/model scoring.

Recorded prior production is not a forecast or current historical position.
Completion clocks and source availability are separate. Nothing here fits a
model, creates canonical State, or authorizes a preference/Decision grade.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite

from fsffl.state.historical_coverage import HistoricalEvidenceKind, HistoricalEvidenceReceipt, HistoricalSeasonIdentity
from fsffl.state.historical_roster_context import HistoricalRosterContextHistory
from fsffl.state.historical_season_lineage import HistoricalSeasonLineage, build_historical_season_lineage
from fsffl.state.historical_trade_context_coverage import HistoricalTradeContextCoverageRow
from .context_inputs import POSITIONS, PartialPositionContext, PartialRosterContext, context_feature_readiness


def _fingerprint(value: str) -> None:
    if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('exact source/scoring SHA256 required')


@dataclass(frozen=True)
class HistoricalPlayerProduction:
    player_id: str  # Provider identity, shared with the admitted roster source.
    position: str | None
    fantasy_points: float
    games: int

    def __post_init__(self):
        if not self.player_id.strip() or (self.position is not None and not self.position.strip()):
            raise ValueError('production player and observed position required')
        if type(self.games) is not int or self.games < 0:
            raise ValueError('observed game count must be a nonnegative integer')
        if isinstance(self.fantasy_points, bool) or not isfinite(self.fantasy_points):
            raise ValueError('observed points must be finite')


@dataclass(frozen=True)
class HistoricalProductionEvidence:
    receipt: HistoricalEvidenceReceipt
    source_sha256: str
    scoring_rules_sha256: str
    players: tuple[HistoricalPlayerProduction, ...]

    def __post_init__(self):
        if self.receipt.kind != HistoricalEvidenceKind.PLAYER_PRODUCTION:
            raise ValueError('player production receipt required')
        _fingerprint(self.source_sha256); _fingerprint(self.scoring_rules_sha256)
        if len({p.player_id for p in self.players}) != len(self.players):
            raise ValueError('duplicate production player identity')


@dataclass(frozen=True)
class HistoricalScoredMatchup:
    team_id: str  # Explicit canonical season mapping, never inferred from names.
    opponent_team_id: str
    points_for: float
    points_against: float

    def __post_init__(self):
        if not self.team_id.strip() or not self.opponent_team_id.strip() or self.team_id == self.opponent_team_id:
            raise ValueError('distinct mapped matchup teams required')
        if any(isinstance(n, bool) or not isfinite(n) for n in (self.points_for, self.points_against)):
            raise ValueError('observed matchup scores must be finite')


@dataclass(frozen=True)
class HistoricalResultsEvidence:
    receipt: HistoricalEvidenceReceipt
    source_sha256: str
    week: int
    matchups: tuple[HistoricalScoredMatchup, ...]
    incomplete_team_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if self.receipt.kind != HistoricalEvidenceKind.MATCHUPS:
            raise ValueError('matchup evidence receipt required')
        _fingerprint(self.source_sha256)
        if type(self.week) is not int or self.week < 1:
            raise ValueError('positive historical week required')
        rows = {m.team_id:m for m in self.matchups}
        if len(rows) != len(self.matchups) or len(set(self.incomplete_team_ids)) != len(self.incomplete_team_ids):
            raise ValueError('duplicate weekly team evidence')
        if set(rows) & set(self.incomplete_team_ids):
            raise ValueError('weekly team cannot be both complete and incomplete')
        for row in self.matchups:
            other = rows.get(row.opponent_team_id)
            if (other is None or other.opponent_team_id != row.team_id
                    or other.points_for != row.points_against or other.points_against != row.points_for):
                raise ValueError('matchup evidence must retain both consistent sides')


@dataclass(frozen=True)
class HistoricalTeamRecord:
    season: HistoricalSeasonIdentity
    weeks: tuple[int, ...]
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float


@dataclass(frozen=True)
class HistoricalTeamCircumstances:
    provider_roster_id: str
    canonical_team_id: str
    roster_size: int | None
    prior_production: tuple[HistoricalPlayerProduction, ...]
    prior_production_season: HistoricalSeasonIdentity | None
    prior_scoring_rules_sha256: str | None
    unknown_prior_production_count: int | None
    records: tuple[HistoricalTeamRecord, ...]
    partial_model_inputs: PartialRosterContext


@dataclass(frozen=True)
class HistoricalTradeCircumstances:
    transaction_id: str
    season: HistoricalSeasonIdentity
    created_at: datetime | None
    completed_at: datetime
    history_id: str
    snapshot_id: str
    teams: tuple[HistoricalTeamCircumstances, ...]
    used_receipts: tuple[HistoricalEvidenceReceipt, ...]
    excluded_evidence_ids: tuple[str, ...]
    evidence_source_sha256: tuple[tuple[str, str], ...]
    issues: tuple[str, ...]
    source_availability_verified: bool = field(default=False, init=False)
    model_version: str = 'historical-trade-circumstances-v1:descriptive-only'
    eligible_for_owner_model_training: bool = field(default=False, init=False)


def build_historical_trade_circumstances(*, coverage: HistoricalTradeContextCoverageRow,
        history: HistoricalRosterContextHistory, lineage: HistoricalSeasonLineage,
        prior_production: HistoricalProductionEvidence | None = None,
        results: tuple[HistoricalResultsEvidence, ...] = ()) -> HistoricalTradeCircumstances:
    """Join supplied, source-bound facts once; retain unknowns and both clocks.

    The context is immediately before completion, NOT creation. A season-scoped
    franchise crosswalk is not independent proof of the owner's entire tenure.
    Full active placement/pick inventory and new quality features are not inferred.
    """
    checked = build_historical_season_lineage(sources=lineage.sources, links=lineage.links)
    request = coverage.request
    sources = {s.season:s for s in checked.sources}
    source = sources.get(request.season)
    allowed_seasons = {request.season}
    parent_by_season = {link.current:link.previous for link in checked.links}
    cursor = request.season
    while cursor in parent_by_season:
        cursor = parent_by_season[cursor]
        allowed_seasons.add(cursor)
    if (source is None or history.league_family_id != request.season.league_family_id
            or history.provider_league_id != source.provider_ref.external_id
            or history.season != request.season.season
            or source.raw_position_or_slot_codes != history.raw_roster_slots
            or source.source_content_sha256 != history.source_sha256
            or request.source_ref != history.source_revision+':'+history.source_sha256):
        raise ValueError('trade circumstances require exact admitted source cohort')
    snapshot = next((s for s in history.snapshots if s.snapshot_id == coverage.roster_snapshot_id), None)
    if (snapshot is None or snapshot.effective_at != request.completed_at
            or snapshot.boundary != 'before_completed_event_batch'
            or request.transaction_id not in snapshot.transaction_ids):
        raise ValueError('trade circumstances require exact pre-completion snapshot')
    bindings = {b.provider_roster_id:b.canonical_team_id for b in source.roster_bindings}
    roster_teams = {t.provider_roster_id:t for t in snapshot.teams}
    if any(r not in bindings or r not in roster_teams for r in request.participant_roster_ids):
        raise ValueError('trade participant lacks admitted source roster mapping')
    member_ok = (coverage.player_membership_context_available and coverage.source_content_verified
        and history.membership_status == 'provisionally_consistent'
        and not snapshot.uncertain_player_ids and not snapshot.membership_uncertainty_reasons)
    issues = set(); used = []; excluded = []; fingerprints = []
    if not member_ok:
        issues.add('pre_completion_membership_unavailable')
    production = None
    if prior_production is not None:
        receipt = prior_production.receipt
        if receipt.season not in allowed_seasons:
            raise ValueError('production belongs to an unregistered historical season')
        if receipt.season.season >= request.season.season or receipt.effective_at >= request.completed_at:
            excluded.append(receipt.evidence_id)
            issues.add('production_not_prior_completed_season')
        else:
            production = prior_production
            used.append(receipt)
            fingerprints.append((receipt.evidence_id,prior_production.source_sha256))
    if production is None:
        issues.add('prior_production_unavailable')
    eligible_results = []; keys = set()
    for evidence in results:
        receipt = evidence.receipt
        if (receipt.season not in sources
                or receipt.season.league_family_id != request.season.league_family_id
                or (receipt.season.season <= request.season.season and receipt.season not in allowed_seasons)):
            raise ValueError('results belong to an unregistered historical season')
        key = (receipt.season, evidence.week)
        if key in keys:
            raise ValueError('duplicate historical result week; revisions require explicit selection')
        keys.add(key)
        mapped = {b.canonical_team_id for b in sources[receipt.season].roster_bindings}
        if any(t not in mapped for m in evidence.matchups for t in (m.team_id,m.opponent_team_id)) or not set(evidence.incomplete_team_ids) <= mapped:
            raise ValueError('results use an unregistered season team')
        if receipt.season.season > request.season.season or receipt.effective_at >= request.completed_at:
            excluded.append(receipt.evidence_id)
            continue
        eligible_results.append(evidence); used.append(receipt)
        fingerprints.append((receipt.evidence_id,evidence.source_sha256))
    if not eligible_results:
        issues.add('completed_results_unavailable')
    ids = [r.evidence_id for r in used] + excluded
    if len(ids) != len(set(ids)):
        raise ValueError('evidence identities must be unique across circumstances')
    position_production = {p.player_id:p for p in production.players
        if p.games > 0 and p.position in POSITIONS} if production else {}
    slots = Counter(source.normalized_slot_codes)
    teams = []
    for rid in request.participant_roster_ids:
        team_id = bindings[rid]
        roster = roster_teams[rid]
        known = tuple(sorted((position_production[p] for p in roster.player_ids if p in position_production),
            key=lambda p:(p.position,-p.fantasy_points,p.player_id))) if member_ok else ()
        by_season = defaultdict(list)
        for evidence in eligible_results:
            if team_id in evidence.incomplete_team_ids:
                issues.add('incomplete_weekly_result')
            for match in evidence.matchups:
                if match.team_id == team_id:
                    by_season[evidence.receipt.season].append((evidence.week,match))
        records = []
        for season, matches in sorted(by_season.items(),key=lambda x:x[0].season):
            matches.sort(key=lambda x:x[0])
            records.append(HistoricalTeamRecord(season,tuple(w for w,_ in matches),
                sum(m.points_for > m.points_against for _,m in matches),
                sum(m.points_for < m.points_against for _,m in matches),
                sum(m.points_for == m.points_against for _,m in matches),
                sum(m.points_for for _,m in matches),sum(m.points_against for _,m in matches)))
        # Prior-season production positions never fill current historical counts.
        inputs = PartialRosterContext(positions=tuple(PartialPositionContext(p,
            direct_starter_requirement=slots[p] if not source.unknown_slot_codes else None) for p in POSITIONS),
            roster_size=len(roster.player_ids) if member_ok else None,
            flex_slot_count=slots['FLEX'] if not source.unknown_slot_codes else None,
            superflex_slot_count=slots['SUPERFLEX'] if not source.unknown_slot_codes else None)
        context_feature_readiness(inputs)  # Reuse the accepted model's input validation.
        teams.append(HistoricalTeamCircumstances(rid,team_id,len(roster.player_ids) if member_ok else None,
            known,production.receipt.season if production else None,
            production.scoring_rules_sha256 if production else None,
            len(roster.player_ids)-len(known) if member_ok and production else None,tuple(records),inputs))
    # Retrospective membership has no independent contemporaneous roster receipt.
    # Individual receipt availability is retained; full availability is not certified.
    return HistoricalTradeCircumstances(request.transaction_id,request.season,request.created_at,
        request.completed_at,history.history_id,snapshot.snapshot_id,tuple(teams),tuple(used),
        tuple(sorted(excluded)),tuple(sorted(fingerprints)),tuple(sorted(issues)))

