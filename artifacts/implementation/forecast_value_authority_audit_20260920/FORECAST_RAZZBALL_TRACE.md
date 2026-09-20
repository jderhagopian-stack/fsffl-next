# Live Forecast / Razzball Authority Trace

Date: 2026-09-20
Live main: `511977b05a76229739946e56adf209ef6ca174ac`

## Conclusion

**Razzball is not double-counted as a provider vote in the live displayed season Forecast.**

It also appears in the preserved two-source preseason lineage used by the frozen future-Forecast / Shapley Intrinsic path. That is a separate time/horizon authority path, not a second vote inside the same live ensemble.

## Live display path

1. Product display helper `fsfflDisplayedProjectionObservation(player)` selects `fantasy_points / season`.
2. The displayed number is `season_fantasy_points_projection` when the backend exposes it, otherwise the selected season Forecast observation mean.
3. Backend `default_live_forecast_loader` calls `build_current_live_forecasts(league_state)`.
4. Current runtime fetchers are uniquely keyed by source id. Razzball appears exactly once as `source_id="razzball"`.
5. The current Razzball fetcher is `RazzballSeasonProjectionSource`, the horizon-isolated full-season source; the older ROS-fumble augmentation source is not the current runtime fetcher.
6. Each source batch is normalized once.
7. `build_authoritative_live_ensemble` rejects duplicate source ids and gives each eligible independent source one equal-weight contribution to a player/metric/horizon group.
8. Groups with fewer than two independent sources fail closed.
9. Provider raw football stats are ensembled first; connected-league fantasy points are derived once afterward.
10. Product team/player views copy those governed Forecast observations; the browser does not recalculate fantasy points.

Tests explicitly cover Razzball 4000 + FFToday 4200 pass yards -> 4100 ensemble, and current runtime then league-scores the ensembled raw stats.

## Preserved preseason / future path

The frozen preseason baseline is a two-source ensemble:
- FFToday
- Razzball

Durable lineage:
- 1,675 raw ensemble observations
- 335 players
- provenance `fsffl:live_equal_weight[fftoday,razzball]`
- minimum two independent sources
- equal weight
- undercovered groups fail closed

The same frozen raw stat vector is scored:
- once under connected-league rules for product Y1;
- once under frozen standard/non-PPR rules for the P0 compatibility coordinate.

P0 then produces Y2/Y3. Future point quantities are translated back to connected-league units by the same-player connected-Y1 / standard-Y1 ratio **once**.

## What this means

Razzball influences:
- the live current-season ensemble when its full-season source is successfully available; and
- the frozen preseason baseline that conditions the separate future/Intrinsic path.

That is not arithmetic double-counting in one same-horizon estimate. It is reuse of one historical/preseason evidence source across a multi-horizon forecast lineage.

Do not describe Y1, Y2 and Y3 as three independent Razzball observations. They are dependent forecast horizons by design.

## Live-log limitation

Hosted logs at the current deploy do not emit a fresh provider-success list containing `razzball`; they only prove the current deployed code coordinate. Therefore the claim above is a code/contract/provenance proof of the live path, not a claim that a new Razzball HTTP fetch was observed in Render logs during this audit.
