# FSFFL NEXT — Product Roadmap

## Current parallel critical paths

### Foundation / league-agnostic path
1. Forecast Research: **COMPLETE**.
2. Management acceptance / bounded implementation authorization: **COMPLETE**.
3. Governed Forecast implementation, evidence-independent scope: **MERGED / COMPLETE at PR #215, main `407c1bf85e5dc75f92b9906719f82bcd11d97c31`**.
   - K and D/ST subject/scoring contracts;
   - active-rule completeness and fail-closed missing evidence;
   - deterministic realized-outcome and non-promoting calibration harnesses;
   - annual raw-snapshot replay invariants.
4. Empirical/source promotion gate: **BLOCKED**:
   - historical independent K/DST source #2;
   - production provider rights/content-health;
   - exact Sleeper D/ST truth fixtures;
   - qualifying 2026 K/DST preseason PIT evidence or explicit preseason unavailability.
5. Resume and complete new-league 7/7 lifecycle acceptance only after the required Forecast authority is actually promoted.

### Product / Market path
1. Prior physical-iPhone Market acceptance: **FAILED / NOT ACCEPTED** as a product gate.
2. Market / Trade Discovery Architecture Review: **COMPLETE**. Handoff: `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`.
3. Management acceptance of revised Opportunity + Market contract: **COMPLETE**.
4. Bounded Market/Search/North Star implementation: **IMPLEMENTATION ACCEPTANCE COMPLETE — PR #220**. Handoff: `artifacts/implementation/market_discovery_north_star_20260925/IMPLEMENTATION_HANDOFF.md`.
5. Merge/deploy PR #220 and repeat physical-iPhone/Safari Market acceptance: **NEXT GATE**.
6. Home × Franchise redundancy/information-hierarchy audit.
7. Trade Center expansion only after discovery/search order of operations is settled.

## Forecast authority boundary
Implemented contracts and research harnesses do not themselves create production K/DST forecasts. No one-source calibration, offensive-position fallback coefficient, aggregate-source double counting, guessed D/ST bucket math, or current/post-opener data backdated as preseason is permitted.

## Why Market architecture moved forward
The shipped Market shell established useful concepts, but physical-iPhone evidence showed:
- a supposedly high-signal For You feed can contain repeated target neighborhoods and packages still requiring substantial evaluation;
- discovery is spending user attention before enough cheap economic/bilateral screening and diversity control;
- Player Board and Free Agents can be unavailable while global readiness reports 7/7;
- Market is denser and less immediately readable/navigable than the accepted North Star surfaces.

This is not treated as presentation polish alone.

## Trade Discovery principle
Simulation should evaluate shortlisted trades, not perform broad discovery.

Working sequence:
`League State → strategic needs/opportunity hypotheses → candidate assets/counterparties → broad cheap package generation → economic screening → bilateral plausibility → clustering/diversity → high-signal opportunity frontier → targeted Decision/Simulation → deeper analysis`

Simulation is a microscope, not the searchlight.

## Product principle
For You should surface a deliberately small number of genuinely distinct strategic opportunities, not merely raw packages Search can construct. The product must be able to explain why each item deserves scarce user attention before asking the user to enter a deep evaluation.

## League-agnostic validation
“League-agnostic” remains a target, not a fully proven property. Forecast implementation and later lifecycle validation must exercise configurations unlike the original FSFFL league without weakening evidence authority.


## Accepted-for-review Market architecture
The completed review proposes:
- strategic hypotheses before targets/packages;
- Opportunity as the scarce-attention object;
- Candidate Paths as concrete acquisition routes;
- raw package neighborhoods as subordinate variants;
- cheap Decision-owned economic screening and a bounded pre-Simulation bilateral screen;
- family clustering/dominance pruning before feed ranking;
- deterministic diversity selection instead of package-row lane diversity;
- maximum four For You opportunities in the private beta, with no duplicate exact target;
- zero broad changed-state Simulation calls;
- Core 7/7 readiness separated from Market consumer readiness;
- opportunity-first For You, progressive Trade Finder, read-only Player Board, and roster-fit-first Free Agents.

Management accepted these policies on 2026-09-25; PR #220 implements them and has satisfied implementation-level automated acceptance.
