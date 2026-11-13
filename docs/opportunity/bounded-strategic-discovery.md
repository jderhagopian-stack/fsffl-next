# Bounded strategic discovery backend

This bounded backend explores multiple trade hypotheses and attaches existing
Decision evidence. The reviewed Explore interface consumes these diagnostic
results while preserving server order and explicit tradeoffs. Discovery does not
promote packages to confirmed recommendations.

`POST /api/opportunities/strategic-discover` accepts an empty body for automatic
priorities, or optional request-scoped instructions:

```json
{
  "search_instructions": {
    "objectives": ["career_contribution"],
    "protected_player_ids": ["owned-player-id"]
  },
  "counterparty_team_id": "another-team-id",
  "target_asset_ref": "player:target-id",
  "max_candidates": 80,
  "evaluation_budget": 8
}
```

Counterparty and target restrictions are optional. A target must belong to an
admitted counterparty; a received pick can be targeted using `pick:pick-id`.
Protections must reference owned players. Instructions override inferred managed
priorities for this request; counterparty motives remain hypotheses. Exact assets
and temporary instructions accompany each `trade_center_request` for subsequent
analysis/Simulation. Returning to automatic mode does not change durable profiles. A protection-only
`search_instructions` object omits `objectives`; the server infers current
priorities and applies the protections without an explicit goal override. An
explicit empty objective list remains invalid.

## Candidate generation

Reuse NEXT6 canonical owned inventories, package identities and bilateral
proposals. Separate lanes explore published roster weaknesses and Forecast
production, 3-Year/Career contribution, native-Intrinsic versus Market rank
ordering disagreement, and transaction structure. Roster strength is a reason to
investigate, not proof of need or expendable supply. Rank disagreements use the
same covered player cohort and respect ties; they are not monetary discounts.
Display indexes are never subtracted from one another or from Market values.

Each lane admits at most six ingredients per side BEFORE enumerating combinations.
The first version supports one or two assets per side, including players, picks,
received picks and mixed packages. It excludes FAAB in this release. Package
traversal rotates shapes, lanes and counterparties deterministically. It does not
build a league-wide unrestricted cross-product.

At most 640 pair visits are allowed (at most eight times the requested return
limit). Duplicate packages merge observed hypothesis provenance. Existing NEXT5
cheap package/Market economics give context for allocating further investigation;
Market equality is neither the target-selection rule nor the recommendation.
A complete pre-cut native-horizon complement can also guide investigation.
Both are provisional until cuts and roster consequences are checked. Categorical
coverage favors different counterparties, hypotheses and outgoing assets; it
contains no weighted master score. Strained or incomplete cases remain visible.

Return at most 80 packages per batch and run at most eight detailed pre-Simulation
screens per request (at most 32 distinct screens per continued search).
The effective screen ceiling also respects the requested return limit. Screens
now precede final retention: every evaluated point, including a failed parent,
survives; remaining result slots preserve categorical exploration. A complete
counterparty future-direction gain can guide investigation when managed Current
is requested, while explicitly leaving the managed current benefit pending.
This partial hypothesis does not establish full complementarity or erase other
requested objectives and sacrifices.

### Bounded feedback

For a Current-inclusive search with matching native ROS, published baseline and
native-horizon evidence, reserve up to eight pair visits **before** generation.
Generation plus repair visits cannot exceed the same original visit ceiling.
Roots and repairs share the same eight unique screen attempts; at most one
two-step repair sequence is attempted, leaving independent roots to explore.
Unused repair screens backfill roots. Duplicate canonical points reuse their
already-attached evidence and are never screened or returned twice.

An eligible root has an adverse managed weekly-point change and known cut-adjusted
future-direction alignment for its counterparty. Existing NEXT6 geometry can
remove a published starter and add an active same-position bench alternative
ordered by the counterparty's admitted native horizon(s). Starter/bench facts
only order hypotheses; they do not establish expendability. The inventory stays
within six ingredients and each package within two assets. Both steps pass the
same corrected weekly Decision screen and unchanged mandatory-cut accounting.
An adequate first step can stop; missing or protected-cut evidence stops the path.
Career-only instructions do not silently become a Current repair objective.

Protected sends, source/publication identity, ownership, counterparty restrictions
and exact received targets are preserved. Receiver packages stay unchanged during
this first repair policy. Non-player repair geometry is not added; general root
generation still supports picks and mixed packages. Missing native coverage is
never assumed zero. Every repair retains root, parent, move, depth and
`hypothesis_only` lineage. Visit/screen budgets, skipped reasons, duplicates and
evaluated retention are explicit diagnostics. This policy explores tradeoffs; it
does not claim that every repaired point is better or grant recommendation truth.

Diagnostics distinguish visited pairs, unique pool packages, returned packages,
omitted exploration, shapes, hypotheses, counterparties, native/rank coverage,
source identity, timing and screen errors. This is a bounded hypothesis sample,
not an exhaustive search or global optimum. A single failed screen does not erase
other candidates. Unknown source values remain missing, including pick Intrinsic.

## Evidence and authority

Existing Decision owns cheap Market/package accounting and both-team before/after
roster, lineup and required-cut consequences. The published native-horizon reader
and [objective assessment](../trade-decision/objective-assessment.md) supply
separate 3-Year/Career ledgers after cuts and both-team directional tradeoffs.
The preliminary screen remains visible even when an inferred future goal points
in another direction; Search does not override Decision domination/action truth.

Current-season competitiveness stays unresolved until authoritative Simulation.
A lineup-point comparison is not a win/playoff/championship forecast. Owner
history remains descriptive context; this release does not learn acceptance
probabilities. All packages remain diagnostic-only and retain sacrifices. Native
asset contribution is not team-specific franchise utility.

Existing NEXT6 Pareto comparison runs only for evaluated packages whose BOTH
requested objective vectors are complete on identical named native coordinates.
Different goal/source-coordinate groups are separate; missing cases are retained,
not treated as dominated. Non-domination within such a group does not promote a
final recommendation, owner willingness or confirmed mutual benefit.

## Resource and publication contract

Read the existing producer record once and validate exact user, league State,
managed team, published generation and dependency fingerprint. Project only small
native-value maps; no large source model/contract is retained by the projection.
A weak reference binds it to the immutable request snapshot without serializing
the entire State again per candidate. It cannot be reused across another snapshot,
user, managed team or generation. The old single-trade reader preserves its output
contract; binding reuses the same Value discount and NEXT5 arithmetic.

Published Forecast and Value, request-local baseline lineups, existing provisional
Forecast attachment and profiles are reused across screens. No model fitting,
Forecast acquisition, Intrinsic game, Monte Carlo run, database payload load or
production write occurs during discovery. Source release/unavailability preserves
partial structural results. Only the bounded response cache described below is added; there is no new
worker, queue or persistence owner. The hosted route uses existing heavy-work admission, rechecks runtime after
admission and returns 409 promptly when busy rather than waiting behind a refresh.

Focused validation covers bounded geometry, all four shapes, source-reader parity,
identity fences, ties/unknowns, explicit directions, received picks, protections
and required cuts, partial failures, single source read, unchanged inputs, no
Simulation, and 12-team Superflex/1-QB contract fixtures. Saved real inputs can be
replayed locally without production changes. Such replay is distinct from hosted
response acceptance, owner-intent validation and confirmed competitive benefit.

## Explore production interface

Explore / For You consumes this API directly. The first read uses automatic
competitive-state direction; owners can switch to request-scoped priorities.
The compact **Refine your search** control follows **Your Direction**, before
results. It supports current canonical counterparties, exact targets, received
player position, required outgoing players or picks, and protected managed players. `target_position` is optional,
validated against the current league player population, and applied to received
inventories before bounded generation. A combined target must match that position.
No league-specific starting positions or fixed team counts are assumed.

The interface preserves server candidate order, separates screened packages from
incomplete exploration, and shows both sides' preliminary lineup changes,
cut-adjusted native horizon contributions, Market costs, coverage, and linked
repair alternatives. Lineup points are explicitly labeled by their returned
basis; they are not wins or playoff probabilities. No saved scenario is shipped
as live intelligence. Native asset contribution is not franchise utility, and
overlapping horizons are not added. Owner motives remain inferred.

Only one discovery request is active per browser context; edits invalidate its
response. Submitting changed settings replaces old results rather than showing
an old package under new priorities. Repeated rendering does not rerun discovery;
there is no polling, automatic retry, automatic Simulation, or new persistence.
State/team/publication changes fence responses and discard request-scoped settings.

Trade Center receives the exact package and temporary instructions. Its quick,
analysis, Simulation, and bounded frontier routes admit the same instructions.
Protections exclude sends before frontier exploration; required cuts that lose
protected players remain explicitly blocked. Frontier assessments retain unknown
future contribution rather than manufacturing native values or claiming a
priority-optimized frontier. Existing Decision ordering/authority is unchanged.
Trade Center displays both teams' directional assessments separately from its
final Decision. Explicitly analyzing a deal uses the existing progressive
quick → analysis → Simulation workflow. Discovery itself never runs that flow.


### Competitive context and first-read grouping

Explore explicitly displays the published calculated competitive state separately
from the automatic search direction and user overrides. The existing provisional
league-relative classification is unchanged: Contender → Current, Competitive →
Balanced (Current/3-Year/Career without weights), Developing → 3-Year, Rebuilding →
Career. Unknown remains visibly unknown with an all-horizon fallback. Published
playoff and championship odds provide context; they are not recomputed.

A presentation-only categorical view groups existing preliminary evidence. Packages
with both-side priority gains and no known requested losses appear first, with
Current still identified as a lineup proxy pending Simulation. Packages with gains
and sacrifices appear under Tradeoffs to review. Known priority losses without a
demonstrated offset remain in expandable comparison history. Missing evidence and
zero-gain cases do not establish a fit. Original generation/evaluation order is
preserved inside each group, and failed parents/linked repairs remain available.
This changes neither Decision authority, intrinsic economics, nor the underlying
unweighted priorities; no composite score or final mutual-benefit claim is added.
The standalone Market vs. Intrinsic discovery button is temporarily removed.

## Continuation and directed offers

The live endpoint wraps each existing at-most-eight-screen batch with bounded
continuation. Responses include `search_progress` with cumulative distinct screens,
preliminary-fit count, stop reason, and optional opaque `next_token`. Send it back
as `continuation_token` with identical instructions. The browser continues toward
four preliminary fits, stopping no later than 32 screens or pool exhaustion; it
preserves prior results, supports pause-after-batch and explicit further screening.

`offered_asset_ref` requires a canonically owned outgoing player or pick in every
package. It is enforced before the six-ingredient enumeration cap and cannot send
a protected player. Received targets/position/partner constraints are unchanged.
For You and Trade Finder share the live engine; Trade Finder opens directed controls.

Tokens carry only signed IDs/progress and bind exact tenant, State/generation,
Forecast/Simulation/Value identities, native-source identity and request settings.
They expire after ten minutes; restart or scope changes return 409. Each search
shares one repair sequence. Cross-batch repair duplicates link to earlier results
and stop rather than assuming missing previous screen details or re-evaluating.

Response reuse is process-local, at most four entries / 4 MiB of accounted response
and key graphs / five minutes. There is no retained State/model/source graph or new
persistence adapter. Noncached concurrent batches fail fast. Existing heavy-work
admission remains in force. Generation can revisit the same at-most-640 cheap pool
per batch; diagnostics describe that work per request rather than implying only
640 CPU visits across all requests. No Forecast, Intrinsic or full Simulation runs
are added. [Pick evidence coverage](pick-economics-coverage.md) remains explicit.
