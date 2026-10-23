# Issue #479 — Roster-universal Intrinsic coverage implementation checkpoint

## Verified causal path
Production artifact `fsffl.derived_artifact.id=12657` contains 359 estimates and these three entries in `player_coverage_failures`: Hill 3321 (no complete Y1 raw scoring row), Aiyuk 6803 and Sarratt 13268 (active-backup missing single-source). Their approved assumption metadata is absent.

In `src/fsffl/product/p0_live_candidate_runtime.py`, `recorded_ytd_only_year_one_evidence(league_state, as_of=min(cutoff, ros_revision_cutoff))` only admits what `recorded_nfl_role_receipts` returns. In `src/fsffl/providers/nfl_status_evidence.py`, `NFL_ROLE_RECEIPTS` is a static tuple of dated facts and `recorded_nfl_role_receipts` filters `row.captured_at <= as_of < row.captured_at + timedelta(hours=6)`. Latest hard-coded captures were 2026-10-20 19:55:28 UTC; expiry is 2026-10-21 01:55:28 UTC. The October 21 artifact saved at 12:15:36 UTC. (State and acquisition cutoffs must be independently checked: artifact save time alone does not establish the exact evidence cutoff.)

The candidate fallback is implemented, but `admit_ytd_only` returns None when the evidence map is empty, leaving generic scoring failures. This explains the recurring symptom and makes manually appending new static receipts an unsustainable solution.

## Engineering sequence
1. Capture the exact `cutoff` and `ros_revision_cutoff` from the failing build; demonstrate missing evidence admission with a regression that uses its real state and cutoff. Preserve prior-State historical fingerprint stability.
2. Introduce a bounded, pluggable, durable **current-role evidence acquisition** mechanism for producer-owned refreshes only. Acquire verifiable evidence when expired (including source, role, observed/captured time, season, canonical identity); do not treat a stale fact as current or attempt network acquisition on GET paths. Build source implementation using existing authorized providers and their actual evidence capture; no fake receipt timestamps. Retain audit history.
3. Replace identity-hardcoded eligibility as the only pathway with policy-driven categories (unsigned, reserve/dispute, developmental/depth, injury/nonparticipation, normal two-source, complete one-source, independently validated projection). Allow YTD-only only when supported by fresh, explicit approved status evidence; no universal implied zero ROS. Preserve per-player confidence and current/future Shapley inputs. Ensure unknown cases still fail closed with clear reason.
4. Consolidate shared decision engine for exact-State Career and Career-derived 3-Year without repeated heavy Shapley; reconcile every rostered QB/RB/WR/TE ID against estimate or explicit unsupported status before publication. Differentiate `computation_complete` from `coverage_complete` in publication/diagnostics without breaking persisted contract compatibility.
5. Introduce parameterized tests for the three failing players, additional player IDs with equivalent evidence, expiring/renewing evidence, incorrect identity/season, role changes, unavailable source, and historical replays. Test missing ROS sources and alternative complete sources, and ensure current-player values are unchanged whenever normal evidence is present.
6. Pass focused/full CI, frozen-reference parity, performance/memory guard, read-only GET proofs, then one monitored hosted refresh and authenticated 12/12 WR room acceptance. No unverified deployment or repeated production computation.

## Guardrails
Maintain 512 MiB hard cap and existing state/fingerprint/publication safety; no changes to Shapley mathematics, prior assumptions, or default fabricated estimates. Last-good artifacts remain available when new work fails. Do not close #405/#479 until verified live and after one subsequent refresh preserves qualifying player coverage.

## Status
Diagnosis and implementation branch created. This checkpoint is not a software fix and does not authorize publication.