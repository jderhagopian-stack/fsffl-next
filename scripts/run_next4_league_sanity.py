from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.providers.acquisition import ProviderBackedStateService
from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.providers.sleeper_snapshot import SleeperSnapshotNormalizer
from fsffl.runtime import Next4LeagueSanityInput, run_next4_league_sanity
from fsffl.team_utility import CompetitiveStatePolicy, FranchiseAssetPortfolio, ScheduledMatchup


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the generic NEXT-4 league sanity harness without persisting league data to git."
    )
    parser.add_argument("--league-id", required=True)
    parser.add_argument("--forecasts", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--competitive-state-policy", type=Path, required=True)
    parser.add_argument("--asset-portfolios", type=Path)
    parser.add_argument("--horizon", default=ForecastHorizon.SEASON.value)
    parser.add_argument("--playoff-teams", type=int, required=True)
    parser.add_argument("--simulations", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=20260905)
    args = parser.parse_args()

    service = ProviderBackedStateService(
        source=SleeperLiveSource(),
        normalizer=SleeperSnapshotNormalizer(),
    )
    league_state = service.materialize_live(league_external_id=args.league_id)
    as_of = league_state.as_of

    forecasts = tuple(ForecastObservation.model_validate(item) for item in _load_json(args.forecasts))
    schedule = tuple(ScheduledMatchup.model_validate(item) for item in _load_json(args.schedule))
    policy = CompetitiveStatePolicy.model_validate(_load_json(args.competitive_state_policy))
    portfolios = (
        {
            team_id: FranchiseAssetPortfolio.model_validate(payload)
            for team_id, payload in _load_json(args.asset_portfolios).items()
        }
        if args.asset_portfolios
        else {}
    )

    result = run_next4_league_sanity(
        Next4LeagueSanityInput(
            league_state=league_state,
            forecasts=forecasts,
            schedule=schedule,
            horizon=ForecastHorizon(args.horizon),
            playoff_team_count=args.playoff_teams,
            competitive_state_policy=policy,
            asset_portfolios=portfolios,
            simulation_count=args.simulations,
            seed=args.seed,
            as_of=as_of,
        )
    )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
