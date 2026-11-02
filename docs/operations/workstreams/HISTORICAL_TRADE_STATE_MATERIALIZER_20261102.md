# Historical trade State materializer — 2026-11-02

## Scope

Backend only. This increment adds a reusable, provider-neutral transformation from an exact pre-trade `LeagueState` to the factual post-trade `LeagueState` for one evidenced bilateral trade. It is not a full season replay, a historical grade, a provider adapter, a database writer, or a deployment.

## Contract

`src/fsffl/state/historical_materializer.py`:

- requires the pre-trade State, exact season identity, source receipt for that roster State, a complete transaction-window receipt, and a normalized trade record;
- refuses a window containing other unapplied transaction IDs and refuses unsupported three-or-more-team destination semantics;
- transfers players, picks, and bilateral FAAB in the canonical immutable State;
- requires individually evidenced receiving roster slots and caller-supplied pre-trade pick / FAAB evidence receipts;
- returns explicit blockers instead of inventing missing slots, pick ownership, or FAAB balances;
- reports whether supplied source evidence was available at the transaction cutoff, while permanently keeping `eligible_for_pit_decision_grade=False`.

Nonparticipant FAAB is not inspected or reconciled by this trade-scoped transition. The isolated $3 nonparticipant archive discrepancy therefore does not block this selected transition.

## Selected 2023 archive disposition

The retained archive replay is still not a canonical pre-trade State. It lacks a certified full pick universe and trade-date roster placement evidence. The new function must therefore return blockers for the archive until an exact State and missing placement evidence exist. That is a concrete, machine-readable boundary; it does not claim that the historic State has been reconstructed.

The Deneric Prince screenshot remains supplemental evidence for a separate August 2023 waiver drop. It is not part of the October trade transaction, and the original source audit remains unchanged.

## Validation

Local focused validation: `tests/test_historical_state_materializer.py`, `tests/test_historical_trade_transition.py`, `tests/test_historical_trade_state.py`, and `tests/test_historical_coverage.py` — **30 passed**. `git diff --check` passed. PR #502 merged as `83fbb699bcc60b836f02b8ff0a5849fee4da55b0` from exact head `e650213f66b797ad6dac9dba7e930b2f033c46c3`. Regular CI [41375337041] and Stable full suite [41375454897] passed; the full suite reported **2,612 passed, 4 skipped** with exact-head checks before and after.

No migration, database write, provider fetch, app change, or deployment occurred.
