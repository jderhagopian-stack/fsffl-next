# API and UI Boundary

FSFFL NEXT must remain usable without any specific user interface.

## Core rule

Model logic lives behind structured application/API contracts. Web, mobile, reports, notebooks, terminals, or future clients consume those contracts and do not reimplement authoritative model logic.

## API responsibilities

The application/API layer may:

- authenticate/authorize callers in future deployments;
- validate request schemas;
- resolve a requested league/team/scenario into canonical state;
- invoke authoritative forecasting, valuation, simulation, decision, opportunity, and analytics services;
- return structured outputs with provenance, version, uncertainty, and explanation metadata;
- support asynchronous execution for expensive work when later justified.

It may not:

- invent alternative valuation logic;
- hide model-version identity;
- convert presentation preferences into unrecorded model assumptions;
- embed provider-specific payloads in core response contracts.

## Presentation responsibilities

Clients may:

- sort/filter/group results;
- render charts, heat maps, trade builders, scenario controls, reports, and narrative explanations;
- persist user-facing display preferences;
- request explicit strategic overrides through typed inputs.

Clients may not silently alter analytical meaning.

## Explanation contract

Important decisions should eventually expose machine-readable explanation components such as:

- key drivers;
- before/after state effects;
- uncertainty;
- counterparty perspective where relevant;
- market-vs-intrinsic distinctions;
- model/evidence versions;
- warnings about missing or provisional evidence.

Narrative prose is a presentation of these structured facts, not an independent source of authority.

## Commercial readiness

This boundary allows the same backend to support:

- personal command-line/research use;
- a web application;
- iOS/Android clients;
- reports;
- future third-party integrations.

Commercial features such as accounts, subscriptions, billing, rate limits, and entitlements are intentionally deferred until needed; the model architecture must not depend on them.
