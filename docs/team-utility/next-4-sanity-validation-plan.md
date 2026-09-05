# NEXT-4 Sanity Validation Plan

This plan applies the FSFFL NEXT charter to behavioral validation of Team Utility & Simulation.

## Charter gate

NEXT must remain league-agnostic and user-agnostic. Therefore one real league may be used as an adversarial sanity environment, but it must not become the universal calibration target or a hidden source of owner-specific preferences.

Validation proceeds in two layers:

1. **Controlled synthetic sanity cases** with explicit expected monotonic behavior and pass/fail assertions.
2. **Real-league adversarial checks** using a current league state to expose interactions that simplified fixtures may miss.

The second layer may surface defects or hypotheses. It may not by itself justify universal coefficients.

## Controlled sanity suite

The initial suite should cover:

- removing an elite QB from a Superflex roster produces a larger team-scoring loss when the next available QB is weak than when QB depth is strong;
- removing an elite WR from a deep WR room produces a smaller lineup loss than removing the same-quality WR from a shallow room;
- adding the same player to two different rosters may produce different marginal lineup and resilience effects;
- adding projected points cannot reduce expected regular-season wins under otherwise identical deterministic inputs except for Monte Carlo sampling noise, which should be bounded/reproducible;
- stronger replacement depth cannot worsen the calculated largest single-player lineup drop;
- owner strategic posture cannot alter calculated competitive state or simulation outputs;
- market/intrinsic asset values cannot alter lineup optimization or competitive simulation unless they change roster composition through an explicit scenario;
- taxi/IR assets cannot be used as active replacements unless canonical state/rules make them eligible;
- identical inputs plus identical simulation seed must reproduce identical outputs;
- missing forecast evidence must be surfaced rather than silently imputed.

## Real-league sanity layer

A connected/user league is appropriate for realistic adversarial validation after the controlled suite passes.

Recommended checks include:

- ranking teams by simulated current-year competitive strength and reviewing obvious outliers;
- inspecting marginal impact of elite QBs, top WRs, starting RBs and premium TEs across rosters with different depth;
- comparing teams with similar broad market value but different current competitive strength;
- comparing fragile top-heavy teams with deeper teams;
- testing a small set of add/remove scenarios where a knowledgeable league participant can state the expected direction before seeing model output;
- recording disagreements as diagnostic cases, not manually overriding model outputs.

User judgment should be recorded as **sanity evidence**, not as a fitted universal parameter.

## Promotion rule

A NEXT-4 behavior is ready for exit only when:

- structural/unit tests pass;
- controlled sanity invariants pass;
- realistic league checks reveal no unexplained severe contradictions;
- any remaining uncertainty is explicitly classified as governed provisional, challenger, or future improvement;
- no correction introduces downstream trade/search/report authority into NEXT-4.

## Efficiency

The controlled suite should run automatically in CI. Real-league checks should reuse the same structured scenario evaluator rather than require bespoke scripts for individual teams.
