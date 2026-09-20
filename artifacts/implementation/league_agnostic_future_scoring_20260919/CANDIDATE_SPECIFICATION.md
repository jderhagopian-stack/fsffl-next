# League-agnostic future scoring candidate — non-authoritative gate specification

Date: 2026-09-19  
PR surface: #147 / `implementation/forecast-intrinsic-i1-shapley`  
Authority boundary: candidate evidence only; not wired into runtime authority.

## Problem

The current future bridge applies one league/standard scoring ratio per position to frozen P0 point outputs. That conversion loses player-specific scoring mix. The bounded candidate keeps frozen P0 intact and moves league scoring to a downstream player-specific representation.

## Candidate

For player `p` and league scoring rules `L`:

1. Preserve the governed frozen Year-1 raw football-stat vector.
2. Score that same Year-1 vector under the frozen P0 standard/non-PPR compatibility rules, producing `Y1_std[p]`.
3. Score the same vector under league rules, producing `Y1_L[p]`.
4. Define the player-specific downstream translation `r[p,L] = Y1_L[p] / Y1_std[p]` when the standard denominator is positive.
5. Keep every frozen P0 state probability and persistence/active probability unchanged.
6. Multiply only scoring-dependent P0 point outputs (state means and their probability-weighted anticipated points) by `r[p,L]`.
7. Apply active probability only in its already-governed downstream location. The candidate does not add a second active-probability application.

For supported linear scoring rules, this is algebraically equivalent to applying P0's frozen conditional-production retention to the player's Year-1 stat vector and then scoring the resulting future vector under league rules. It therefore preserves the player's stat mix without requiring P0 to forecast each future stat category independently.

## Fail-closed behavior

The candidate fails closed when a required player has no matching standard Year-1 observation, when positions disagree, when a league score is nonzero but the frozen standard denominator is zero, or when a multiplier is non-finite/non-positive.

## Non-authority

The candidate module is deliberately separate from `private_beta_shapley_runtime.py` and the existing position bridge. No runtime producer, production authority, main branch, merge, or deploy is changed by this gate.

## Validation boundary

The exact identity/parameters of the interrupted run's sixth scoring configuration were not durably persisted and could not be recovered from repository or prior management evidence. The continuation therefore does not invent a replacement. It revalidates the five required/recoverable scoring families and the exact connected league, then relies on the algebraic invariant for arbitrary supported linear rules.

The connected league's current Year-1 scoring also contains bounded provisional residuals (for example two-point conversions / rare scoring events) in the existing scoring engine. The candidate consumes the governed Year-1 league score, so those governed additions remain represented in the player-specific ratio rather than being silently dropped.

## Promotion boundary

A PASS here means the no-refit translation itself is sufficient and P0 need not be reopened. It does not authorize runtime wiring, merge, deploy, or a change to production scoring coverage.
