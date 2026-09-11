# FSFFL NEXT — Phase 3 Visual Intelligence Grammar

Status: product/presentation contract

This document governs how already-owned FSFFL intelligence is expressed in the product. It does not create State, Forecast, Value, Decision, Search, Simulation, Behavioral, or historical truth.

## Product reading order

Every major surface should deliver intelligence in this order:

1. **See** — a scan-first visual summary that answers the user’s question.
2. **Understand** — concise plain-language drivers and context.
3. **Interact** — tap, compare, filter, expand, or run the next action.
4. **Drill deeper** — exact evidence, sources, methods, and provenance.

Default product copy is written for a fantasy manager. Internal architecture language belongs in Methods & Evidence unless it is necessary to avoid a misleading conclusion.

## Four interaction layers

### Layer 1 — Scan

Show the decision-relevant conclusion and the smallest number of visuals needed to make it legible.

Examples:
- 83% playoff chance
- WR #1 of 12 — strongest WR room in the league
- +0.7 expected wins after this trade
- Worth investigating — RB need meets another team’s RB surplus

### Layer 2 — Explain

Show the most important drivers in consumer language.

Examples:
- RB is your weakest starting position.
- This team has one of the league’s deepest RB rooms.
- The player you are sending comes from your deepest position.
- The package is close to the current value range.

### Layer 3 — Evidence

Expose exact governed measurements and source-backed detail when requested:
- player and pick values
- optimized lineups
- league-relative position measurements
- projection sources
- Simulation outcomes/distributions
- replacement exposure
- package economics
- counterparty effects
- owner-history evidence
- historical evidence

### Layer 4 — Methods

Expose technical provenance and model mechanics without making them part of the normal first read:
- model/version identifiers
- simulation counts
- evidence source metadata
- uncertainty/missingness
- authority boundaries
- methodology and calibration notes

## Visual vocabulary

Use a visual when it communicates an existing governed fact faster or more clearly than prose or a raw list. Do not turn every number into a chart.

| Governed information | Preferred default expression | Drill-down |
| --- | --- | --- |
| Probability | ring/gauge or compact probability bar | Simulation distribution, assumptions, sources |
| League-relative strength | indexed bar + ordinal rank | exact index, lineup contributors, source projection |
| Rank | ordinal + league denominator/context | full league ranking |
| Before/after consequence | paired bars, delta band, arrow/shift | exact baseline/scenario values |
| Simulation outcome | probability shift, trajectory, distribution | run count, full distribution, assumptions |
| Positional league structure | heat map / atlas | exact position measurements by team |
| Roster construction | position profile / depth visualization | player-level roster and optimized lineup |
| Age/value horizon | timeline / distribution / league band | exact ages, values, horizon assumptions |
| Draft capital | year-by-year trajectory/band | pick inventory and exact values |
| Trade package | side-by-side asset comparison | package economics and alternatives |
| Owner behavior | tendency profile | evidence examples, recency, transaction history |
| Uncertainty | confidence/evidence indicator | source quality, missingness, methodology |
| Change over time | delta/sparkline/direction | prior-state comparison and timestamps |

## Semantic status language

Visual prominence must never imply authority that the underlying application does not have.

### Recommended

Use only when the authoritative Decision/application path grants recommendation/action authority.

### Worth investigating

Use for a strong Search/market opportunity that has useful structural evidence but has not earned a full recommendation.

### Needs full evaluation

Use when a candidate is plausible but bilateral/changed-roster Decision evidence is incomplete.

### Market match only

Use when Search identifies structural/value proximity without sufficient evidence to imply improvement or recommendation.

Never substitute a presentation score, fit percentage, acceptance probability, or color treatment for these authority states.

## Consumer-language rules

Primary copy should state what the user needs to know, not how the system is architected.

Prefer:
- `WR #1 of 12 — strongest WR room in the league`
- `83% playoff chance`
- `Largest one-player lineup loss: 4.8 points`
- `Worth investigating — addresses your weakest position`

Avoid in Layer 1/2:
- governed
- authoritative
- canonical
- presentation layer
- Decision owns
- Search retained
- NEXT-2 / NEXT-3 / NEXT-4
- internal schema or pipeline names

Those terms may appear in Methods & Evidence where useful.

## Metric clarity contract

Every prominent metric must make clear, directly or through a nearby label:

- what the number means;
- the relevant time horizon;
- whether higher/lower is favorable;
- how it compares with the league when comparison is material;
- what player/team/position is driving it when that attribution is available.

If a raw governed metric is not naturally interpretable, the first read should present a contextualized derivative that is mathematically/semantically faithful and presentation-only, while preserving the exact underlying measurement in drill-down. No arbitrary multiplier or hidden score is permitted.

## Surface jobs

- **Home:** What matters right now?
- **Franchise:** What is driving my team?
- **League:** How does this league fit together?
- **Market:** What moves are worth my attention, and what level of authority do they have?
- **Trade Center:** Does this trade make me better, what does it cost, and what changes?
- **Simulator:** How does this scenario change my future?
- **League Impact:** How does this move change the competitive ecosystem?
- **Owners:** How does this manager tend to behave, and what evidence supports that?

Each surface should have a distinct visual composition appropriate to its question rather than a shared wall of generic metric cards.

## Architecture boundary

The authoritative pipeline remains:

Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation

The visual-intelligence layer may select, order, compress, compare, and explain facts already returned to it. It may not create model truth, recommendation authority, acceptance probability, behavioral contamination of universal Value, or a hidden master score.
