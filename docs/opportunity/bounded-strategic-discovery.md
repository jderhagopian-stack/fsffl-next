# Bounded strategic discovery backend

This opt-in backend explores multiple trade hypotheses and attaches existing
Decision evidence. The current Explore interface and default ForYou ordering are
unchanged. Review the mobile mockup and real-league usefulness before activation.

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
analysis/Simulation. Returning to automatic mode does not change durable profiles.

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

Return at most 80 packages and run at most eight detailed pre-Simulation screens.
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
partial structural results. There is no new cache, worker, queue or persistence
owner. The hosted route uses existing heavy-work admission, rechecks runtime after
admission and returns 409 promptly when busy rather than waiting behind a refresh.

Focused validation covers bounded geometry, all four shapes, source-reader parity,
identity fences, ties/unknowns, explicit directions, received picks, protections
and required cuts, partial failures, single source read, unchanged inputs, no
Simulation, and 12-team Superflex/1-QB contract fixtures. Saved real inputs can be
replayed locally without production changes. Such replay is distinct from hosted
response acceptance, owner-intent validation and confirmed competitive benefit.
