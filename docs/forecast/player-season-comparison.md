# Player season comparison

Player Intelligence's Career & Forecast tab compares the captured preseason
projection, finalized actual points, remaining-season projection, and their
combined season outlook. Overview uses that same saved outlook when available.
The career trajectory and annual model baselines continue directly below season
progress in the normal card scroll, using the same panel style and readable
typography. Forecast years remain compact in a horizontal strip. Career histories scroll
horizontally while a separate, fixed point-scale column remains visible on the
left; both SVGs use identical vertical coordinates and scale bounds. Intrinsic economics and Simulation are unchanged.

## Authority and provenance

`forecast/season_comparison.py` consumes the existing governed in-season
orchestration and league scoring. Weekly actuals must agree with the canonical
State's season and completed-week boundary; future weeks cannot enter actuals.
Actuals and ROS describe disjoint periods. The live ROS evaluation cutoff is
established after actual acquisition and includes their capture time; provider
provenance keeps its original timestamps. This preserves the roll-forward guard
against evidence that postdates its evaluation cutoff. The terminal season uses actuals only.
Source facts reuse the existing projection-history owner at provider/horizon/week
scope; league-scored results remain State-scoped.

The original preseason benchmark is read through its immutable baseline's exact
linked historical artifact, with league/season isolation, matching raw inputs,
and identical scoring rules. This is a comparison with what was actually saved,
not a backdated projection reconstructed with today's fumbles model. If the
original scored snapshot cannot be verified, only complete captured statistics
may be scored under current rules, explicitly labeled. Missing coordinates remain
unavailable. No archive is overwritten or synthesized.

ROS preserves the shared ensemble first. Explicitly qualified single-source
fallbacks must pass the accepted first-party fumbles-lost projection. The shared
ensemble's source minimum is unchanged. A player without an NFL team has zero
remaining projection and retains earned actuals. Acquisition-wide failure can
use the existing labeled preserved remaining prior; this is not described as a
fresh provider projection. Missing evidence and partial coverage remain visible.

## Refresh, reads and resources

`product/season_comparison_runtime.py` prepares one compact artifact through the
existing owned refresh callback and heavy-work coordinator. It does not add a
worker, thread pool, lifecycle controller, startup fitting, or GET-time acquisition.
Producers are serialized; readers do not wait on provider work. State ownership
is checked before and after preparation. The artifact is keyed by exact State
and model version; a two-State in-process cache bounds retention. Explicit retry
can update the same State. A database miss requests a normal refresh.

One baseline-linked historical read selects only the required fields using the
existing bounded pooled PostgreSQL owner. One comparison artifact is persisted
per preparation, rather than one artifact per player. Player requests return only
one row. Optional comparison failure does not invalidate core intelligence.
The refresh phase is instrumented as `forecast.season_comparison` for production
runtime/RSS evidence. No schema, hosting, or compute-plan change is needed.

## Chart semantics and validation

The cumulative actual line represents finalized weekly scores. The preseason
line is a reference pace, and the ROS connector illustrates the remaining total;
neither is a saved weekly forecast. Only existing governed ROS quantiles create
an uncertainty band. Missing totals and signed fantasy points remain explicit.

Focused tests protect actuals-plus-ROS arithmetic, snapshot preservation,
completed-week mismatch, unsigned players, mandatory fumbles completion,
season completion, bounded cache, restart reads, no GET-time production,
State-switch ownership and pooled archive reads. Synthetic responsive Chromium
checks cover 320, 375, 390 and 768 pixel widths with no horizontal overflow.
A synthetic 875-player/nine-week composition measured approximately 1.16 seconds,
541 KB serialized output and 30 MiB incremental process high-water memory.
This excludes network acquisition and model fitting and is not a hosted refresh
measurement. Production numerical acceptance requires a normal authenticated
refresh after deployment.

## Shared participation exceptions

`forecast/participation.py` owns the unchanged accepted receipt eligibility
previously housed in the Intrinsic live candidate integration. Both consumers
use the same functions; existing Intrinsic imports remain compatible. Confirmed
season unavailability, approved roster-role assumptions and exact-State IR with
no source rows can yield actuals plus zero ROS. Ordinary missing evidence, IR
with source rows, and generic bench/taxi membership cannot independently create
zero projections. Complete current projections keep existing precedence; unsigned
status retains its accepted priority. The UI labels verified unavailability
separately from an actuals-only assumption and retains source/version/capture
provenance. Role evidence keeps its existing freshness fence. A real owned live
refresh may use the same bounded official reserve/left-squad acquisition as
Intrinsic (at most four roster pages, five-second request timeout); injected
or historical evaluations do not acquire newer role facts. No new source rule,
valuation formula, preseason rewrite or GET-time acquisition is introduced.
