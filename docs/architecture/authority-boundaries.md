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

## Behavioral Intelligence evidence authority
Owns point-in-time evidence about observed manager behavior derived from provider history and other admissible historical actions. It may maintain reusable owner/league profiles, evidence volume, transaction-shape tendencies, asset-direction patterns, and relationship history. It does **not** own market Value, competitive outcomes, franchise utility, acceptance percentages, or action recommendations.

Behavioral evidence is an upstream input to Decision when evaluating negotiation plausibility, owner-specific reservation context, and other explicitly behavioral questions. Small samples and missing history remain visible rather than being converted into hidden certainty. Behavior-conditioned counterfactual branches may consume this same evidence, but they must remain distinct from Simulation's authority over football outcomes.

## Decision authority
Owns franchise utility deltas, bilateral trade effects, roster consequences, strategic outcomes, and the governed interpretation of Behavioral Intelligence for a specific decision. Competitive state is calculated; owner strategic posture is an explicit input/override. Behavioral evidence may inform owner/team-specific decision context but cannot rewrite general market Value.

## Simulation authority
Simulation is authoritative for modeled competitive outcomes when those outcomes require stochastic season or matchup resolution. Other layers may consume simulation results but not independently invent competing win-impact estimates. Human behavioral branching in a counterfactual is a separate evidence-conditioned process and must not be relabeled as football simulation.

## Search authority
Search generates candidates and explores feasible frontiers. It cannot change values to make packages balance and cannot grant action authority to unvalidated candidates. It may consume Behavioral/Decision evidence for plausibility or ordering only through an explicit governed contract.

## Analytics authority
Analytics derives descriptive and comparative views from authoritative outputs. It is read-only with respect to model authority.

## Presentation authority
Reports and UI explain and visualize. They must not contain hidden decision coefficients, thresholds, or valuation logic.

## Anti-double-counting rule
A real-world effect should enter authoritative utility once. Supporting evidence may be visible in multiple views, but repeated presentation is not repeated valuation. Behavioral evidence that already affects a governed Decision output must not be independently added again by Search or Presentation.

## Challenger rule
Alternative methods may run in parallel as challengers. They are non-authoritative until promoted through evidence-backed validation.
