# FSFFL NEXT Architecture Overview

## Purpose

FSFFL NEXT is organized around one-directional authority:

`Data -> Point-in-Time State -> Forecast -> Value -> Decision -> Search/Optimization -> Analytics/API -> Presentation`

Each layer owns a distinct class of truth. Downstream layers consume upstream outputs; they do not recreate the same concept independently.

## Core layers

### Data
Raw and normalized facts from providers. No valuation or recommendation logic.

### Point-in-Time State
Canonical, timestamped reconstruction of league, team, player, pick, rules, roster, transaction, injury, and known-environment state.

### Forecast
Probabilistic future outcomes: player production, availability, development, aging, pick outcomes, and uncertainty.

### Value
Transforms forecast distributions and market information into asset and franchise value representations. Market price, intrinsic value, team-specific value, and likely transaction price remain distinct concepts.

### Decision
Evaluates state changes for one or more teams. Owns bilateral franchise utility and strategic consequences.

### Search / Optimization
Generates and searches candidate actions. It may ask the Decision layer to score possibilities but cannot invent its own value logic.

### Analytics / API
Read-only derived views and stable structured contracts for reports, terminal, web, mobile, and other clients.

### Presentation
Human-facing explanation and interaction. Presentation may filter, sort, and explain authoritative outputs but may not silently alter model conclusions.

## Foundational properties

- Point-in-time reproducibility is mandatory.
- Model, evidence, parameter, and provider versions are explicit.
- Expensive deterministic or stochastic intermediates are cacheable.
- Historical evaluation must prevent future-information leakage.
- League rules are configuration, not hard-coded assumptions.
- Sleeper is an adapter, not the domain model.
- Legacy FSFFL is evidence and a research corpus, not an authority source.

## NEXT-0 exit condition

No substantial valuation implementation should begin until domain objects, authority boundaries, state semantics, evidence lifecycle, versioning, and validation contracts are documented and internally consistent.
