# Live Value Runtime Integration Slice

## Purpose

Wire the already-governed NEXT-3 Value authority into the private-beta runtime after the now-credible NEXT-2/NEXT-4 forecast and simulation path.

This is integration work, not a redesign of Value authority.

## Architectural placement

Authoritative flow remains:

Data -> State -> Forecast -> **Value** -> Decision -> Search/Optimization -> Analytics/API -> Presentation

The product/runtime layer may orchestrate current Value evidence and expose results, but must not invent valuation coefficients, rankings, thresholds, or substitutions.

## First implementation target

Build a league-wide current asset-value runtime that:

1. Acquires the governed current NEXT-3 market source panel through existing provider adapters.
2. Preserves source failures and lineage rather than treating missing providers as zero evidence.
3. Resolves market evidence to current canonical State asset identities.
4. Produces typed authoritative MarketPriceEstimate outputs where evidence requirements are met.
5. Adds intrinsic/pick/transaction estimates only where their governed mappings/calibrations are explicitly available; absence must remain explicit.
6. Stores Value evidence against the exact LeagueState/evidence lineage so stale Value cannot attach to a newer state.
7. Exposes a read-only product/API payload suitable for player/pick value tables and later Team Utility / Trade Decision consumers.

## Product outcome

Once this slice is live, the beta should be able to show league-wide asset values and Value readiness without presentation-layer calculation. This unlocks the next downstream sequence:

**Team Utility portfolios -> bilateral Trade Decision -> Search/Opportunity Engine.**

## Validation

- exact-state lineage rejection for stale Value evidence;
- provider failure isolation;
- identity-resolution coverage diagnostics across the full league roster;
- no downstream imports into `fsffl.value`;
- no frontend valuation logic;
- exact-head CI before beta deployment.
