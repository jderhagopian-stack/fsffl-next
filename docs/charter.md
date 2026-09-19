# FSFFL NEXT — Project Charter

FSFFL NEXT is a clean-sheet redesign of the FSFFL dynasty fantasy football intelligence platform.

The purpose of NEXT is not to reproduce the current FSFFL implementation more neatly. It is to use everything learned from building, auditing, testing, debugging, calibrating, and using the existing system to build a substantially better long-term architecture.

## Core Objective

Build a dynasty decision-intelligence platform that is:

- more accurate and empirically defensible;
- easier to understand and audit;
- faster and more computationally efficient;
- modular and easier to extend;
- safer to modify without creating hidden interactions or double counting;
- capable of learning and recalibrating as evidence improves;
- league-agnostic and user-agnostic;
- suitable for a future interactive website or application;
- architecturally capable of commercial scale if that path is chosen later.

## Relationship to Legacy FSFFL

The existing `jderhagopian-stack/sleeper-league-data` repository remains operational and may continue to be used for league analysis, experimentation, reports, and research.

It is a **reference implementation and source of accumulated knowledge, not the specification for NEXT**.

Existing FSFFL outputs, coefficients, architecture, assumptions, or implementation choices must not be presumed correct merely because they already exist.

NEXT may produce materially different results from legacy FSFFL when those results are better supported by evidence, cleaner reasoning, sound football economics, simulation, historical calibration, or a superior model architecture.

The objective is **validated superiority, not legacy parity**.

## First-Principles Rule

Every material concept inherited from legacy FSFFL must earn its place in NEXT.

Classify existing concepts as appropriate:

- RETAIN
- RE-DERIVE
- REDESIGN
- RETIRE
- INVESTIGATE

No coefficient, heuristic, adjustment, signal, or model behavior should survive solely because the old system used it.

Where evidence is incomplete but a real effect should not reasonably be ignored, NEXT may use a bounded and explicitly documented provisional prior. Such estimates should be designed for future empirical updating.

## Architectural Principle

The preferred directional flow is:

**Data -> Point-in-Time State -> Forecast -> Value -> Decision -> Search/Optimization -> Analytics/API -> Presentation**

Each concept should have one clearly defined authoritative home.

Downstream modules should consume authoritative outputs rather than independently recalculating or reinterpreting the same concept.

The system should actively prevent:

- double counting;
- duplicated authority;
- circular dependencies;
- hidden adjustments;
- unexplained hard-coded coefficients;
- presentation-layer business logic;
- module-specific reinvention of shared concepts.

## Point-in-Time Architecture

Historical reconstruction is a foundational capability, not an add-on.

The system should eventually be capable of reconstructing what was reasonably knowable at a historical point in time and running an appropriate version of the model against that state.

This supports:

- historical trade calibration;
- pick-value reconstruction;
- projection evaluation;
- coefficient estimation;
- model comparison;
- behavioral studies;
- backtesting;
- evidence-based promotion of challenger models.

Future information must not contaminate historical evaluation.

## Evidence and Parameters

Material model parameters should carry explicit provenance and, where relevant:

- definition;
- authority;
- evidence source;
- estimation method;
- uncertainty;
- version;
- effective date;
- update mode;
- dependencies;
- calibration history.

Parameters may be static, structurally derived, empirically estimated, evidence-updating, or bounded provisional priors depending on their nature.

The preferred question is not:

> Is the current coefficient reasonable?

It is:

> Is there a more defensible way to determine this?

## Forecasting

Projection and forecasting should be first-class platform capabilities.

NEXT should support multiple replaceable projection/data providers, internal FSFFL forecasting, source-specific historical evaluation, uncertainty distributions, position-specific performance, and ensemble approaches where empirically justified.

External providers should be adapters rather than permanent architectural dependencies.

Data provenance and licensing considerations should be recorded so future commercialization does not require architectural reconstruction.

## Value and Decision Intelligence

NEXT should distinguish concepts such as:

- market price;
- intrinsic dynasty value;
- value to a particular team;
- value to a counterparty;
- likely transaction price;
- future outcome distributions;
- competitive impact;
- long-term franchise utility.

These should not collapse into one universal asset number when the underlying concepts are different.

Team competitive state and owner strategic preference should remain separate concepts.

## Trade Architecture

Trade functionality should separate:

**Candidate Generation -> Bilateral Evaluation -> Price Discovery -> Behavioral Plausibility -> Opportunity Ranking**

The mathematical ability to balance a trade does not by itself make the trade realistic or desirable.

Both sides of a transaction should be evaluated using consistent authoritative utility.

## Simulation

Simulation should remain authoritative for competitive outcomes where appropriate.

Expensive calculations should be reusable and cacheable.

NEXT should prefer incremental/delta computation when mathematically valid rather than unnecessarily rerunning complete simulations for every nearby scenario.

Large Monte Carlo samples, including approximately 50,000 simulations where useful and computationally appropriate, remain desirable.

## Product Architecture

NEXT should be designed from inception for:

- multiple users;
- multiple leagues;
- configurable scoring and roster rules;
- multiple fantasy platforms;
- interchangeable data providers;
- structured APIs;
- model versioning;
- reproducible outputs;
- caching;
- background-ready compute architecture;
- frontend independence.

Sleeper should be one connector, not the underlying data model.

A future website, iOS/Android application, or other interface should consume structured NEXT services rather than contain model logic.

Commercial features do not need to be built now, but the architecture should not prevent them later.

## Modules

Future capabilities should be able to plug into shared authoritative services.

Potential applications include, but are not limited to:

- Trade Decision;
- Opportunity Engine;
- League Intelligence / Analytics;
- Draft Intelligence;
- Waiver Intelligence;
- Simulator;
- Counterfactual / What-If;
- Breakout / Sleeper analysis;
- projection research;
- roster construction;
- negotiation assistance;
- reports;
- interactive UI tools.

New modules should not create parallel versions of shared core concepts.

## Validation Philosophy

NEXT is not required to match legacy FSFFL.

Important differences should instead be evaluated through:

- historical evidence;
- out-of-sample testing where possible;
- projection accuracy;
- simulation;
- market behavior;
- football-economic reasoning;
- sanity cases;
- uncertainty;
- internal consistency.

For important model changes, comparisons should ideally record:

- legacy result;
- NEXT result;
- reason for the difference;
- supporting evidence;
- confidence/uncertainty;
- decision to adopt, revise, or continue investigating.

A cleaner architecture alone does not prove greater predictive accuracy.

Likewise, disagreement with legacy FSFFL is not evidence of failure.

## Development Strategy

Build FSFFL NEXT in a separate repository.

Legacy FSFFL remains usable while NEXT develops.

Do not perform a mechanical port of the legacy repository.

Before implementing a major legacy concept, understand what problem it was intended to solve and determine the best current way to solve that problem.

Development should proceed through small, reviewable, well-tested changes rather than an enormous rewrite.

The initial milestone is **NEXT-0: Architecture & Foundation**.

NEXT-0 should define:

- project architecture;
- canonical domain objects;
- point-in-time state model;
- module authority;
- data/provider boundaries;
- evidence and parameter architecture;
- model/version architecture;
- validation strategy;
- commercial/API boundary;
- legacy concept inventory;
- ordered implementation roadmap.

Only after those foundations are coherent should substantial valuation/decision-model implementation begin.

## Guiding Standard

FSFFL NEXT should be built as though it may need to support this platform for many years.

Optimize for correctness, evidence, modularity, transparency, replaceability, testability, performance, and future evolution rather than preserving historical implementation decisions.

The goal is not to rebuild FSFFL.

The goal is to build the platform we would have designed originally if we had known everything we know now.
