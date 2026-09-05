# NEXT-4 Team Utility & Simulation Plan

NEXT-4 answers: **What does this asset or roster actually do for this team?**

It consumes canonical point-in-time league state from NEXT-1, football forecasts from NEXT-2, and economic value representations from NEXT-3. It may not rewrite any upstream authority.

## Authority split

1. **Team state / lineup** — determine the best legal lineup from the actual roster and league rules.
2. **Replacement impact** — measure marginal player contribution by re-optimizing the same roster without that player. Do not substitute an arbitrary league-average starter.
3. **Competitive simulation** — estimate wins, playoff probability, first-place/title-style probability, floor/upside and fragility from forecast distributions.
4. **Franchise utility** — preserve competitive impact, future asset strength, depth, resilience and optionality as distinct typed channels unless an evidence-backed mapping explicitly combines them.
5. **Strategic posture** — owner preference remains separate from calculated team state and may be applied downstream without changing calculated reality.

## Implementation milestones

NEXT-4 establishes:

- deterministic exact lineup optimization under canonical lineup requirements;
- FLEX and SUPERFLEX eligibility derived from position, not hardcoded player premiums;
- taxi and IR excluded from active lineup availability;
- missing forecast evidence surfaced rather than silently imputed;
- marginal lineup impact measured against the team's actual optimized replacement path;
- uncertainty-aware team scoring distributions with explicit provisional independence assumption;
- reproducible competitive simulation with explicit schedules and seeds;
- calculated competitive-state outputs under explicit versioned policy;
- roster resilience from actual replacement pathways;
- non-collapsing team utility vectors;
- explicit calculated-state vs owner-strategy contracts;
- structured before/after scenario deltas without trade recommendation authority;
- a generic runtime sanity harness that can evaluate a live league without storing league data in git;
- controlled and real-league sanity validation before NEXT-4 exit.

## Runtime path

The runtime sanity harness follows the charter direction:

**runtime provider acquisition -> canonical NEXT-1 state -> explicit NEXT-2 forecast inputs -> NEXT-4 lineup/scoring/simulation/utility -> structured diagnostics**

It does not infer forecasts, schedules, competitive-state thresholds, owner preferences, trades, reports, or presentation behavior.

## Anti-double-counting rule

A real-world effect enters final team utility once. NEXT-3 market/scarcity economics are consumed as upstream economic evidence; NEXT-4 adds only the team-specific roster and competitive consequence. A QB cannot receive a generic Superflex bonus here merely because the market already values Superflex scarcity.

## Downstream boundary

- Bilateral trade evaluation belongs to NEXT-5.
- Search/package balancing belongs to NEXT-6.
- Reports, analytics, charts and API presentation belong to NEXT-7.
- Interactive product UI belongs to NEXT-8.
