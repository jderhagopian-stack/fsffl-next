# League Atlas v1 — structured visual description

Date: 2026-09-21

## Mobile-first scan order

1. **League Atlas hero** — one plain-language read of the managed franchise's strongest and weakest position plus current contender/rebuilder counts. It explicitly says the page keeps different evidence in separate governed lanes rather than one power score.
2. **Positional control map** — one row per franchise and one cell each for QB/RB/WR/TE. Cells carry the governed league rank and strength index; background emphasis makes strong/middle/weak rooms visually scannable. The managed team is highlighted.
3. **Player value map** — toggle between **Broad Market**, **FSFFL Intrinsic**, and **Difference**. Every franchise gets a horizontal player distribution strip. Dots are individual rostered players; the surface does not calculate a team average, total, or rank. Tapping a franchise opens exact player rows with Market percentile, Intrinsic percentile, and governed percentile gap.
4. **Pressure point** — for the managed franchise, the weakest governed position is called out with the strongest current positional rooms elsewhere in the league. Copy explicitly says this is descriptive supply, not a trade recommendation or partner-fit score, and hands investigation to Market.
5. **Competitive shape + age** — compact lanes for existing calculated competitive state and a side-by-side age band using canonical roster/starter averages and known-age coverage.
6. **Future flexibility** — horizontal bars show owned draft-pick inventory only. No Cardinal total, summed percentile, or universal team-value coordinate appears.
7. **Depth & fragility** — collapsed by default. Expansion reveals existing Team Utility roster-resilience evidence such as forecasted bench count and largest one-player lineup drop.
8. **Evidence & definitions** — collapsed supporting detail naming authority boundaries, unavailable concepts, and the browser-session Atlas load measurement.

## Progressive drill-down

The first screen is designed to answer “how do these franchises differ?” without methodology text. Exact position indexes, player-level Value evidence, age coverage, resilience, and authority definitions remain one tap/expand deeper.

## Unavailable behavior

Broad Market and Shapley Intrinsic are independently available. If the value-lens request fails, the structural Atlas still renders and Value is explicitly unavailable. Missing position/utility evidence is not replaced with a presentation-derived score. Trade-partner fit remains unavailable until an existing Search/Decision contract supplies it.

## Explicit non-features

The v1 surface creates no team Intrinsic total/rank, no summed Broad Market percentile, no League Market Value, no owner-adjusted universal Value, no acceptance probability, no recommendation strength, and no hidden composite/power grade.
