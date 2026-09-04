# Authority Boundaries

FSFFL NEXT uses explicit ownership to prevent duplicated logic and double counting.

## Data authority
Owns provider ingestion, normalization, identifiers, timestamps, provenance, and source confidence. It does not score assets or teams.

## State authority
Owns the canonical point-in-time representation of what is known. State objects are immutable snapshots or versioned derivations from immutable events.

## Forecast authority
Owns probabilistic future performance and uncertainty. It may combine multiple projection sources and internal models, but must expose provenance and model version.

## Value authority
Owns conversion of forecast distributions, scarcity, replacement environment, horizon, liquidity, and market evidence into value representations. Distinct value concepts must remain separately typed.

## Decision authority
Owns franchise utility deltas, bilateral trade effects, roster consequences, and strategic outcomes. Competitive state is calculated; owner strategic posture is an explicit input/override.

## Simulation authority
Simulation is authoritative for modeled competitive outcomes when those outcomes require stochastic season or matchup resolution. Other layers may consume simulation results but not independently invent competing win-impact estimates.

## Search authority
Search generates candidates and explores feasible frontiers. It cannot change values to make packages balance and cannot grant action authority to unvalidated candidates.

## Analytics authority
Analytics derives descriptive and comparative views from authoritative outputs. It is read-only with respect to model authority.

## Presentation authority
Reports and UI explain and visualize. They must not contain hidden decision coefficients, thresholds, or valuation logic.

## Anti-double-counting rule
A real-world effect should enter authoritative utility once. Supporting evidence may be visible in multiple views, but repeated presentation is not repeated valuation.

## Challenger rule
Alternative methods may run in parallel as challengers. They are non-authoritative until promoted through evidence-backed validation.
