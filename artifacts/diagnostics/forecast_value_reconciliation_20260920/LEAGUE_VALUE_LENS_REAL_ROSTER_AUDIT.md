# League value-lens real-roster audit

Date: 2026-09-20  
Workflow: `35542514540`  
Artifact: `league-value-lens-real-roster-audit` / `10615003350`

## Result

**PASS.** The merged `/api/league/value-lenses` contract was exercised against the real 12-team Sleeper league `1312071960615731200` (`FSFFL Dynasty`) with current live rosters.

Observed coverage:
- 244 rostered player rows;
- 220 rostered players with both Broad Market and Shapley Intrinsic available;
- 522 Broad Market player estimates in the current market runtime;
- 335 Shapley Intrinsic player estimates in the frozen/reconciled population;
- HTTP route returned 200;
- route contract version: `phase3-league-value-lenses-v1`.

Current successful Broad Market sources in this run:
- Dynasty Dealer;
- FantasyCalc;
- Stats Guy.

DynastyProcess was unavailable in the current run and remained an explicit failed source rather than being fabricated.

## Independence checks

The contract passed the exact independence conditions required by management:
- with Broad Market evidence removed, Shapley Intrinsic remained `ready`;
- with Shapley Intrinsic forced unavailable, Broad Market remained `ready`;
- no silent substitution occurred;
- `Difference` equals `Intrinsic percentile - Broad Market percentile` exactly;
- raw Market and Intrinsic values were never subtracted.

The returned authority block confirmed:
- `team_value_total_created = false`;
- `team_value_rank_created = false`;
- `league_market_value_available = false`;
- `team_utility_included = false`;
- `fsffl_cardinal_value_included = false`;
- `recommendation_authority = false`;
- `acceptance_probability = null`.

## Representative real-roster disagreements

| Team | Player | Pos | Broad Market | Shapley Intrinsic rank | Gap |
| --- | --- | --- | ---: | ---: | ---: |
| PVos | Eli Stowers | TE | 67.3th pct | 19.3th pct | -48.0 pp |
| Ballard22 | Drew Lock | QB | 48.7th pct | 2.2th pct | -46.5 pp |
| Anthonyder | Ty Simpson | QB | 75.8th pct | 30.6th pct | -45.2 pp |
| jimmygoodjob | Antonio Williams | WR | 71.9th pct | 31.2th pct | -40.7 pp |
| jder52 | Kirk Cousins | QB | 53.1th pct | 15.7th pct | -37.4 pp |
| chuckthegoat77 | Tank Dell | WR | 46.1th pct | 10.9th pct | -35.2 pp |
| jder52 | Josh Jacobs | RB | 73.9th pct | 47.0th pct | -26.9 pp |

These are diagnostic comparison coordinates only. They do not create a buy/sell instruction, acceptance probability, team value, League Market Value, or Team Utility score.

## Conclusion

The #161 League value-lens contract is ready as an Atlas input contract. Broad Market and Shapley Intrinsic are independently populated on real rostered players and can be compared by presentation percentile without one silently replacing the other.
