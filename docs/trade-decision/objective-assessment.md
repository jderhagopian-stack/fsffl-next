# Directional trade objective assessment

Trade Center analysis and successful Simulation responses add a separate
`objective_assessment`. Existing calculated results and final dispositions remain
unchanged. This is a foundation for discovery, not a new opportunity ranking,
franchise utility model or owner acceptance forecast.

Both teams receive an objective context. The managed user can supply optional
`search_instructions` containing `objectives` and `protected_player_ids` on
`/api/trade-center/analyze` and `/api/trade-center/simulate`. For example:

```json
{"objectives":["career_contribution"],"protected_player_ids":["player-id"]}
```

Supported objectives are `current_competitiveness`, `three_year_contribution`,
`career_contribution`, `resilience` and `market_capital`. Empty/duplicate goals,
foreign protected players and proposals sending protected players are rejected
before calculation. Required cuts to protected players explicitly violate the
constraint. Protection is an evaluation constraint; this release does not change
the accepted mandatory-cut selection policy to optimize a different roster.
Unsupported routes reject instructions rather than silently ignoring them.
Explicit instructions override inferred goals for this request, not another
owner's wishes or a persistent owner profile.

Without instructions, the existing calculated competitive state and posture map
supply a transparent initial hypothesis: win-now emphasizes current competitive
outcomes; retool emphasizes 3-Year contribution; rebuild emphasizes Career
contribution. Balanced/unknown retains all three without weights. This qualitative
policy is an unverified preference hypothesis, not learned owner intent. Owner
history is not used for this inference. Unknown state remains discoverable in the
upstream posture response; the assessment source declares the hypothesis.

Decision assesses native directional changes independently. Requested gains and
losses produce mixed alignment. Missing requested channels produce incomplete
assessment; losses outside the requested objectives remain visible as sacrifices.
A gain is an exact sign, not proof of materiality or statistical significance.
There is no master score, weighted sum, new materiality threshold, automatic
SUPPORT promotion, global-optimum claim or bilateral acceptance probability.

Current competitiveness uses expected wins, playoff probability and regular-season
first-place probability from authoritative Simulation. First place is not a title.
Pre-Simulation analysis and progressive previews cannot confirm this objective.
Resilience uses the existing largest-player lineup-loss exposure, where a smaller
loss is better. Market consumes the existing roster-adjusted market delta.

The two Intrinsic objectives consume independent raw asset-contribution ledgers
with required-cut costs charged exactly once, using the same State/source/horizon
as sent and received assets. They are not a measure of actual team-specific
franchise utility. Overlapping 3-Year/Career horizons are not combined. Missing
pick/FAAB/player/cut evidence withholds that adjusted total. Zero and signed
values are preserved. No cut evidence is distinct from confirmed zero cuts.

The memory-only raw source read now includes only selected players plus required
cuts. It reuses the existing Decision roster resolution and producer/publication
proof, without recalculation, restoration, new storage, workers, cache identity or
source-model changes. The old two-argument provider remains supported; the hosted
three-argument provider receives the calculated result. Source/assessment failures
preserve existing trade results and expose unavailable supplemental evidence.

Tests establish contract behavior and local API integration. They do not establish
that inferred preferences match real owners or that bounded discovery finds useful
trades. Those require retained real-league cases and the next discovery milestone.
Explore ranking and the redesigned UI remain separate; review the mobile mockup
before exposure.
