"""Factual trade timing and asset direction; no owner-intent or strength model."""
from datetime import date,datetime,UTC,timedelta
from typing import Literal
from pydantic import Field,model_validator
from fsffl.state.models import FrozenModel


class HistoricalSeasonWindow(FrozenModel):
    season: int
    first_game_date: date
    regular_season_end_date: date
    season_end_date: date
    source_sha256: str

    @model_validator(mode='after')
    def coherent(self):
        if not self.first_game_date<=self.regular_season_end_date<=self.season_end_date:
            raise ValueError('ordered season calendar boundaries required')
        if len(self.source_sha256)!=64 or any(c not in '0123456789abcdef'for c in self.source_sha256):
            raise ValueError('season calendar source hash required')
        return self


class HistoricalCaseRecord(FrozenModel):
    season: int
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    ties: int = Field(ge=0)
    through_week: int = Field(gt=0)
    regular_season_complete: bool = False

    @model_validator(mode='after')
    def coherent(self):
        if self.wins+self.losses+self.ties!=self.through_week:
            raise ValueError('contiguous weekly record required')
        return self


class HistoricalCaseAsset(FrozenModel):
    kind: Literal['player','pick','faab']
    asset_ref: str
    position: str | None = None  # Dated production evidence, never today's label.


def historical_trade_timing(at: datetime, *, season: int, windows):
    """Use supplied calendar facts. Missing results never imply offseason.

    Dates within the accepted two-day completion bound remain unknown because
    a game date does not prove kickoff or completion time. Source provider season and event calendar year stay separate.
    """
    if len({w.season for w in windows})!=len(windows):raise ValueError('select one admitted calendar revision per season')
    day=at.astimezone(UTC).date();admitted=tuple(w for w in windows if abs(w.season-season)<=1)
    for w in admitted:
        if any(bound<=day<=bound+timedelta(days=2) for bound in (w.first_game_date,w.regular_season_end_date,w.season_end_date)):return 'unknown',None
        if w.first_game_date+timedelta(days=2)<day<w.regular_season_end_date:return 'regular_season',w.season
        if w.regular_season_end_date+timedelta(days=2)<day<w.season_end_date:return 'postseason',w.season
    future=sorted((w for w in admitted if day<w.first_game_date),key=lambda w:w.first_game_date)
    if future and day.year>=future[0].season-1:return 'offseason',future[0].season
    return 'unknown',None


def historical_trade_phase(at, *, season, windows):
    return historical_trade_timing(at,season=season,windows=windows)[0]


def historical_record_text(record, *, trade_season):
    standing=f'{record.wins}–{record.losses}'+(f'–{record.ties}'if record.ties else '')
    if record.regular_season_complete:
        return (f'Finished the {record.season} regular season {standing}',
            f'They finished the {record.season} regular season {standing}.')
    if record.season!=trade_season:
        return (f'{record.season} record: {standing} through Week {record.through_week}',
            f'In {record.season}, they were {standing} through Week {record.through_week}.')
    return (f'{standing} through Week {record.through_week}',
        f'They were {standing} through Week {record.through_week}.')
