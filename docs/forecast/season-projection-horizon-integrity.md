# Season projection horizon integrity

Full-season projections and remaining-season projections describe different
periods. Never average their raw statistics together, or assign a season window
to a remaining-season row merely because a page includes the season year.

The current season source adapter rejects explicit ROS or weekly assertions in
Razzball page titles, headings and table captions. Navigation links to other
products do not establish the table's horizon. Generic year/title wording alone
is also insufficient protection against a numerically changed page, so the
provider-neutral source-health gate checks scale before ensemble construction.

The gate retains its existing empirical multiplicative tolerance and cohort
minimums. It checks both the upper factor and its reciprocal: the same relative
disagreement must have the same disposition whichever dataset is the numerator.
Broad downward shifts require agreement across several positions, just as upward
shifts do. Individual injured players or isolated positional changes do not
trigger a dataset rejection. Provider values are never clipped or multiplied.
With no independent reference and only two disagreeing providers, both remain
unresolved. With several peers, an outlier must disagree with at least two peers.

Live admissions made under the older one-sided health contracts cannot silently
restore as currently validated live evidence. Historical rows are preserved.
The existing resilient loader retains the two-source requirement and uses the
immutable, previously accepted multi-source preseason baseline when live season
sources fail admission. It labels that evidence `preseason_baseline`, preserves
its raw inputs and timestamps, and applies current league scoring and the
existing first-party fumbles-lost completion authority. Without valid live or
preserved baseline authority, refresh fails closed and publication remains with
the previous generation.

## Season to date plus rest of season

`forecast/in_season_orchestration.py::build_governed_in_season_outlook` already
loads finalized weekly actuals and composes them with disjoint ROS periods via
`forecast/season_rollforward.py`. It reports missing per-player evidence, preserves
actuals, supports governed fumbles-lost completion, and identifies any preseason
remaining-prior fallback. The authenticated `/api/forecast/in-season/outlook`
route exposes that result. Live Career candidates also use finalized actuals
plus ROS through `product/p0_live_candidate_runtime.py`, including accepted
single-source fumbles completion and unsigned-player YTD-only handling.

The main roster full-season Forecast still uses the existing full-season loader
and its preseason fallback. This correction does not promote the diagnostic
in-season outlook into that main path or change reference-cohort Intrinsic Y1
authority. Such integration requires a separate review of raw-stat versus
fantasy-point authority, cutoff/finalization, uncertainty, regular-season windows,
coverage and downstream Simulation dependencies. Earned actuals must not be
double-counted, and unsupported statistics must remain unavailable.

Validation covers explicit horizon conflicts, benign navigation/revisions,
bidirectional and peer-only scale disagreements, rejection before averaging,
legacy live-cache invalidation, immutable-baseline fallback with unchanged
scored totals, plus existing in-season and fumbles-loss regressions.
