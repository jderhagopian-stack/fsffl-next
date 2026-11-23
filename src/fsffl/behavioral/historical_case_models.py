"""Compact source-bound historical case, not a learned owner preference."""
from datetime import datetime
from typing import Literal
from pydantic import field_validator,model_validator
from fsffl.state.models import FrozenModel
from .historical_trade_context import HistoricalCaseRecord,HistoricalCaseAsset


class OwnerHistoricalTradeCase(FrozenModel):
    case_id: str
    event_id: str
    event_sha256: str
    league_family_id: str
    owner_id: str
    provider_league_id: str
    transaction_id: str
    roster_id: int
    season: int
    created_at: datetime
    completed_at: datetime
    evidence_as_of: datetime
    activity_through: datetime
    activity_sha256: str
    sent: tuple[str,...]
    received: tuple[str,...]
    situation: str | None = None
    football_season: int | None = None
    trade_phase: Literal['offseason','regular_season','postseason','unknown'] = 'unknown'
    calendar_source_sha256: tuple[str,...] = ()
    record_context: HistoricalCaseRecord | None = None
    acquired_assets: tuple[HistoricalCaseAsset,...] = ()
    disposed_assets: tuple[HistoricalCaseAsset,...] = ()
    retained_players: tuple[str,...] = ()
    context_sentences: tuple[str,...] = ()
    history_id: str
    snapshot_id: str
    source_sha256: str
    circumstance_evidence_sha256: str
    owner_display_name: str | None = None
    attribution_basis: Literal['initiating_account_and_admitted_roster_binding','user_attested_tenure_and_admitted_roster_binding'] = 'initiating_account_and_admitted_roster_binding'
    tenure_reference: str | None = None
    context_clock: Literal['before_completion'] = 'before_completion'
    learned_preference: Literal[False] = False
    model_version: str = 'owner-historical-trade-case-v1'

    @field_validator('created_at','completed_at','evidence_as_of','activity_through')
    @classmethod
    def aware(cls,value):
        if value.tzinfo is None or value.utcoffset() is None:raise ValueError('case clocks must be aware')
        return value

    @model_validator(mode='after')
    def valid(self):
        for s in (self.case_id,self.event_id,self.league_family_id,self.owner_id,self.provider_league_id,self.transaction_id):
            if not s.strip():raise ValueError('historical case identity required')
        for digest in (self.event_sha256,self.source_sha256,self.circumstance_evidence_sha256,self.activity_sha256,*self.calendar_source_sha256):
            if len(digest)!=64 or any(c not in '0123456789abcdef'for c in digest):raise ValueError('case source hash required')
        if self.completed_at<self.created_at or self.evidence_as_of<self.completed_at or self.roster_id<1:raise ValueError('invalid historical case boundary')
        if self.activity_through<self.completed_at or self.activity_through>self.evidence_as_of:raise ValueError('invalid historical activity window')
        if self.attribution_basis=='user_attested_tenure_and_admitted_roster_binding' and not (self.tenure_reference or '').strip():
            raise ValueError('attested case requires tenure reference')
        if self.record_context is not None and self.record_context.season>self.season:
            raise ValueError('future season cannot describe a past trade')
        if self.trade_phase!='unknown' and not self.calendar_source_sha256:
            raise ValueError('trade phase requires calendar evidence')
        if not self.sent and not self.received:raise ValueError('historical case requires an exchange')
        return self
