"""Factual post-transaction witness, never an at-the-time valuation or grade.

A historical trade's recorded sends do not encode asset recipients for 3+ teams;
therefore this first slice rejects multi-party transactions rather than guessing.
"""

from __future__ import annotations

from enum import StrEnum
from pydantic import model_validator

from .historical_coverage import HistoricalEvidenceKind, HistoricalEvidenceReceipt, HistoricalSeasonIdentity
from .historical_trade import HistoricalTradeRecord
from .models import FaabAsset, FrozenModel, LeagueState, PickAsset, PlayerAsset


class TransitionStatus(StrEnum):
    VERIFIED = "verified_fact_transition"
    MISMATCH = "observed_assets_do_not_match_trade"
    AMBIGUOUS = "other_movements_between_snapshots"
    UNSUPPORTED = "unsupported_three_plus_party_destination"


class HistoricalTradeTransitionProof(FrozenModel):
    """Only says two backed snapshots agree with a source-backed trade.

    VERIFIED does not imply PIT Forecast/Value/Decision evidence exists, nor
    that an archived source was publicly knowable by the trade date.
    """

    season: HistoricalSeasonIdentity
    transaction_id: str
    before_state_id: str
    after_state_id: str
    status: TransitionStatus
    differences: tuple[str, ...] = ()
    scope: str = "retrospective_facts_only"

    @model_validator(mode="after")
    def validate_proof(self) -> "HistoricalTradeTransitionProof":
        if self.status == TransitionStatus.VERIFIED and self.differences:
            raise ValueError("verified factual transition cannot include discrepancies")
        return self


def _owner_of_players(state: LeagueState) -> dict[str, str]:
    return {entry.player_id: team.team_id for team in state.team_states for entry in team.roster}


def _owner_of_picks(state: LeagueState) -> dict[str, str]:
    return {row.pick_id: row.owner_team_id for row in state.pick_ownership}


def verify_historical_trade_transition(
    *,
    season: HistoricalSeasonIdentity,
    trade: HistoricalTradeRecord,
    before: LeagueState,
    after: LeagueState,
    before_receipt: HistoricalEvidenceReceipt,
    after_receipt: HistoricalEvidenceReceipt,
) -> HistoricalTradeTransitionProof:
    """Require immutable original-state receipts and check actual asset movement.

    The check is deliberately strict for an isolated single-trade evidence pair.
    Intervening waiver moves or source inconsistencies are flagged as ambiguous,
    never silently attributed to the trade. Caller must establish snapshots are
    from an original verified provider/archive, not rebuild them from current facts.
    """
    for state, receipt in ((before, before_receipt), (after, after_receipt)):
        if state.league.league_id != season.league_id or state.league.season != season.season:
            raise ValueError("cross-league/season State cannot witness a historical trade")
        if receipt.season != season or receipt.kind != HistoricalEvidenceKind.ROSTERS:
            raise ValueError("verified roster receipt must match exact historical season")
        if receipt.available_at is None or receipt.availability_basis is None:
            raise ValueError("roster source availability not verified")
        if receipt.effective_at != state.as_of:
            raise ValueError("roster evidence timestamp must match the exact snapshot")
    if trade.league_id != season.league_id:
        raise ValueError("historical transaction belongs to another league")
    if not (before.as_of < trade.completed_at <= after.as_of):
        raise ValueError("historical snapshots do not bracket the trade date")
    if before.league.rules != after.league.rules:
        raise ValueError("a separate historical rules-change event must be reconciled")
    if {t.team_id for t in before.teams} != {t.team_id for t in after.teams}:
        raise ValueError("season team identity changed between witness snapshots")
    if {p.pick_id for p in before.draft_picks} != {p.pick_id for p in after.draft_picks}:
        raise ValueError("draft-pick universe changed between witness snapshots")

    common = dict(season=season, transaction_id=trade.transaction_id,
                  before_state_id=before.state_id, after_state_id=after.state_id)
    if len(trade.legs) != 2:
        return HistoricalTradeTransitionProof(**common, status=TransitionStatus.UNSUPPORTED,
            differences=("trade sender legs do not identify 3+ party destinations",))

    a, b = trade.legs
    owners_before = {"player": _owner_of_players(before), "pick": _owner_of_picks(before)}
    owners_after = {"player": _owner_of_players(after), "pick": _owner_of_picks(after)}
    faab_before = {s.team_id: s.faab_balance for s in before.team_states}
    faab_after = {s.team_id: s.faab_balance for s in after.team_states}
    expected_transfers: dict[tuple[str, str], tuple[str, str]] = {}
    sent_faab = {a.team_id: 0, b.team_id: 0}
    issues: list[str] = []

    for sender, receiver in ((a, b), (b, a)):
        for asset in sender.sends:
            if isinstance(asset, FaabAsset):
                sent_faab[sender.team_id] += asset.amount
                continue
            kind = "player" if isinstance(asset, PlayerAsset) else "pick"
            asset_id = asset.player_id if isinstance(asset, PlayerAsset) else asset.pick_id
            key = (kind, asset_id)
            if key in expected_transfers:
                issues.append(f"duplicate_transfer:{kind}:{asset_id}")
                continue
            expected_transfers[key] = (sender.team_id, receiver.team_id)
            if owners_before[kind].get(asset_id) != sender.team_id:
                issues.append(f"wrong_pretrade_owner:{kind}:{asset_id}")
            if owners_after[kind].get(asset_id) != receiver.team_id:
                issues.append(f"wrong_posttrade_owner:{kind}:{asset_id}")
    for sender, receiver in ((a, b), (b, a)):
        expected = faab_before.get(sender.team_id, -1) - sent_faab[sender.team_id] + sent_faab[receiver.team_id]
        if faab_after.get(sender.team_id) != expected:
            issues.append(f"faab_mismatch:{sender.team_id}")
    if issues:
        return HistoricalTradeTransitionProof(**common, status=TransitionStatus.MISMATCH,
            differences=tuple(sorted(set(issues))))

    # An otherwise matching trade is NOT a clean single-event witness when
    # different players, picks, or FAAB elsewhere moved at the same time.
    extraneous: list[str] = []
    for kind in ("player", "pick"):
        old, new = owners_before[kind], owners_after[kind]
        for asset_id in sorted(set(old) | set(new)):
            if old.get(asset_id) != new.get(asset_id) and (kind, asset_id) not in expected_transfers:
                extraneous.append(f"other_asset_change:{kind}:{asset_id}")
    for team in sorted(set(faab_before) | set(faab_after)):
        if team not in sent_faab and faab_before.get(team) != faab_after.get(team):
            extraneous.append(f"other_faab_change:{team}")
    if extraneous:
        return HistoricalTradeTransitionProof(**common, status=TransitionStatus.AMBIGUOUS,
            differences=tuple(extraneous))
    return HistoricalTradeTransitionProof(**common, status=TransitionStatus.VERIFIED)
