# FSFFL NEXT

FSFFL NEXT is a clean-sheet redesign of the FSFFL dynasty fantasy football intelligence platform.

The project is intended to become a modular, evidence-updating, point-in-time-reproducible decision-intelligence platform that can support personal use today and future web/app/commercial scale without inheriting legacy implementation constraints.

## Governing principle

Legacy FSFFL is a reference implementation and source of accumulated knowledge, **not the specification for NEXT**. NEXT is expected to differ when a different result is better supported by evidence, cleaner reasoning, football economics, simulation, historical calibration, or a superior architecture.

The objective is **validated superiority, not legacy parity**.

## Directional architecture

`Data -> Point-in-Time State -> Forecast -> Value -> Decision -> Search/Optimization -> Analytics/API -> Presentation`

Each concept should have one authoritative home. Downstream modules consume authoritative outputs rather than independently recreating shared logic.

## Initial milestone

**NEXT-0: Architecture & Foundation**

NEXT-0 defines the project architecture, canonical domain objects, point-in-time state model, authority boundaries, evidence/parameter lifecycle, model versioning, validation strategy, future API/UI boundary, legacy concept inventory, and ordered implementation roadmap before substantial model implementation begins.

See [`docs/charter.md`](docs/charter.md) for the governing project charter.
