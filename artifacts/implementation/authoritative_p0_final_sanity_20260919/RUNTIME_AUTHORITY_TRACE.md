# FSFFL NEXT - P0 runtime authority trace

Date: 2026-09-19

The implemented authority path is:

1. Preserved FFToday + Razzball preseason raw football-stat evidence (1,675 governed ensemble observations; raw-array SHA-256 `4dd1fa70b9b4f886ad103a2f5b6f45f7c4f123a571f84b7a4400b0004271639d`).
2. Direct Year-1 scoring under the connected league rules for product Y1.
3. Direct scoring of the same frozen raw stat vector under the frozen standard/non-PPR compatibility rules for P0 input.
4. Exact frozen P0 package `ea8b5c158d6e08071fe7b1ff2f8ec3538844213e8738ca1f399a1416fe156aa7`.
5. Y2 universal D1; Y3 frozen position x career-stage D0/D1 routing, with P0 persistence/state probabilities and the package's internal prior-two D1 features unchanged.
6. Player-specific downstream league translation = same-player connected-league Y1 / standard Y1. Only future point quantities are scaled; probabilities and persistence are unchanged.
7. Direct Y1/Y2/Y3 calendar.
8. Settled Intrinsic/Shapley consumer and 0.85 annual discounting remain unchanged.

The private-beta runtime no longer instantiates or calls legacy `FrozenI1Artifact` predictors for Y2/Y3. The legacy activation bundle is retained only for existing metadata/evidence-coverage compatibility and is not the future-year producer.

No old separate M1a layer or old separate two-prior layer is applied on top of P0. D1's internally fitted prior-two features remain exactly as serialized in the frozen package.

The standard and connected-league sanity boards are the same 335-player P0 trajectories on two scoring views. Their horizon retention ratios are invariant under player-specific scoring, by construction.
