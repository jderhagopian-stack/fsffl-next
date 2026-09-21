# Player Intelligence + Value Presentation Authority Inventory

Date: 2026-09-21
Base main: d7b1a22157aaa52aebda5e4751e02756629b3029
Directive: Player Intelligence + Value Presentation Upgrade

## Roadmap hold

PR #163 remains open/draft/unmerged and is not modified by this branch.
Market / Opportunities v1 remains blocked.

## Broad Market evidence and shared presentation ruler

Current governed Broad Market authority remains `dynasty-market-percentile`
(`next3-v1`). The current Market runtime also preserves provider-native market
magnitudes before percentile conversion in
`CurrentMarketValueRuntimeResult.native_magnitude_observations`.

Current live retained native distributions contain three independent governed
market evidence families:
- Dynasty Dealer: 537 observations, native min 0, median 2,375, p95 6,946.6,
  p99 8,680.6, max 9,821.
- FantasyCalc: 390 observations, native min 3, median 1,147.5, p95 5,881.8,
  p99 9,115.94, max 11,072.
- Stats Guy: 373 observations, native min 1, median 206, p95 4,528.4,
  p99 8,257.64, max 10,000.

The evidence clearly contains a nonlinear elite tail. A provider-neutral
presentation-only ruler is supportable without inventing an exponent:
1. min-max normalize each retained provider-native distribution independently to
   [0, 10,000];
2. evaluate each normalized empirical quantile at percentile p;
3. use the median source quantile as the shared display index at percentile p.

On the live evidence, representative shared ruler points are approximately:
- p00 = 0
- p25 = 225
- p50 = 1,034
- p75 = 2,025
- p90 = 3,760
- p95 = 5,311
- p99 = 8,257
- p100 = 10,000

This preserves the observed nonlinear elite tail and is not percentile x 100,
not a fitted exponent, not a named-player calibration, and not FSFFL Cardinal.
Both Broad Market percentile and Shapley Intrinsic cross-player percentile may
map through the same ruler without changing either underlying authority.

## Historical player-season evidence

FSFFL NEXT does not currently persist a canonical player-season actual-stat
table. Existing durable history tables cover State snapshots, behavior,
projection history, market history, and historical Analytics artifacts.

An already-authorized canonical Data source DOES exist:
`src/fsffl/providers/sleeper_weekly_stats.py`.
It acquires measured regular-season weekly NFL stat lines from Sleeper and
explicitly declares those rows Data-layer evidence only. Historical actuals can
therefore reuse this source rather than creating a new provider or a
presentation-only raw-history store.

Implementation should aggregate prior regular seasons from this source,
calculate fantasy points under current LeagueRules when point-in-time historical
rules are unavailable, label that scoring basis honestly, and retain Sleeper
source/version/capture provenance. Positional finish must remain unavailable
unless a defensible historical position population can be established.

## Forecast trajectory authority

Current Y1 fantasy points come from the governed current Forecast evidence in
the runtime / Franchise team view.

Y2/Y3 already have a stable Forecast-owned contract:
`FutureForecastContract` / `FuturePlayerHorizonForecast`.
Each row exposes:
- central_expectation;
- target season / year index;
- scoring coordinate;
- model/source;
- uncertainty kind;
- optional stddev / p10 / p50 / p90;
- governed discrete scenarios when supplied.

Current P0 production authority emits Y2/Y3 league-scored central expectations
with discrete scenarios. Product code must read this contract directly and must
not back-solve future points from Intrinsic.

## Value Disagreement inconsistency

Franchise and Market share the same server-side Shapley background coordinator,
but the Market client keeps a state/team scoped terminal cache. If a first
Market request returns an unavailable payload during an evidence-readiness
window, that unavailable payload is retained for the entire state/team context
and is not automatically revalidated when the shared Intrinsic/Market evidence
later becomes ready. Franchise can therefore render ready evidence while Market
still displays a cached unavailable result.

Correction should:
- centralize server-side availability semantics for the Broad Market + Shapley
  pair;
- keep fail-closed behavior;
- make client-side unavailable evidence retryable / invalidated on governed
  evidence readiness rather than permanently terminal for that state.

## Owner-facing Cardinal containment inventory

PR #164 removed Cardinal from core Home/Franchise/primary Trade asset display,
but owner-facing leaks remain, including:
- `analytics_terminal.js`: player tables, divergence, Value Lab, coverage copy;
- `explorer.js`: primary sortable FSFFL Cardinal Value column, rankings and
  summary cards;
- `market_trade_drilldown.js`: owner-facing package / roster-adjusted Cardinal
  terminology;
- `market_trade_recomposition.js`: primary Trade Center result card labels
  Cardinal after cuts.

Compatibility-only backend fields may remain where Decision/Search currently
need them. Presentation must describe those bilateral outputs as governed
package economics / market context without relabeling them as FSFFL Intrinsic.

## Authority boundaries

This branch must not change:
- Forecast coefficients, provider weights, source-health thresholds, or the
  immutable Sep-10 baseline;
- Shapley mathematics;
- Broad Market percentile authority;
- Decision or Team Utility authority;
- PR #163.

The 0-10,000 Value Index is Presentation only. It may authorize subtraction of
two DISPLAY indices because both are on the same versioned presentation ruler;
raw Market and raw Shapley quantities remain non-comparable and are never
subtracted.
