# Career Coverage Extension — Issue #405 implementation checkpoint

Updated: 2026-10-07  
Status: **design/trace complete; implementation not started**  
Authority: [Issue #405](https://github.com/jderhagopian-stack/fsffl-next/issues/405) and [Current Operations](../CURRENT_OPERATIONS.md). This is a separate Career/Foundation 4 workstream, not Architecture Recovery.

## Decision and scope

The frozen 335-player cohort remains the validated calibration/reference cohort, but cannot remain the production valuation ceiling.

For an exact evaluated League State, the accounting population is every rostered QB/RB/WR/TE, regardless of starter, bench, IR or taxi slot. Each must produce a governed Career-forward estimate or a player-specific model-authority failure. A failure remains visible and keeps #370's existing completeness gate closed; it is never converted to zero or hidden by a slot filter.

The valuation population is the 335-player reference cohort, plus the exact-State rostered offensive population, plus only individually requested/discovery-relevant out-of-core players. An unrostered candidate can be valued before acquisition but is not inserted into any team's roster/room accounting. Broad Sleeper-database materialization is explicitly out of scope.

Market/Search/Waiver/Opportunity/Trade/What-If/explicit lookup may identify a candidate. Market remains a separate coordinate and is not a numeric Career Intrinsic input.

## Reconciled preserved-State evidence

The read-only audit memo and Issue #405 were checked against the preserved State, not a newer State:

- League: `sleeper:1312071960615731200`
- State: `606ba3cd0acf427f6724665546dfcbcce0013e593abb658277466c2725b7d2d3`
- Publication generation: `e0114f9704b395150c676c7c258adac1156e754d551e56863e11718b39db7e96`
- As-of: 2026-10-06 05:36:57Z / 01:36:57 ET
- Career artifact: 335 estimates; fingerprint `f6083b680656e52c593a52ba143fbe99fd6d1412aa7eb7e0c05e69fa72eef114`.
- Gap: **25 unique rostered IDs**, confirmed directly from exact roster arrays (5 QB, 8 RB, 10 WR, 2 TE). The prior “22” count is a summary-count error; no alternate preserved 22-player set was found. All listed players were absent, not wrong-position or malformed Career estimates. Do not apply these counts to a later State without a fresh exact-State audit.
- Room coverage was QB 8/12, RB 7/12, WR 4/12, TE 10/12. #370 correctly failed closed.
- Root cause: frozen 335 Forecast/model evidence universe propagated through Current/Y4–Y7/terminal into Career Forward. Not #370, roster-slot filtering, position mapping, or P0 serving/lifecycle.

The complete 25-player list remains in Issue #405; this checkpoint intentionally avoids duplicating it.

## Exact cohort-boundary trace at main `e80db462499dee891dd5ff21a20d322b74d0e5e7`

| Horizon/component | Current boundary | Extension seam |
|---|---|---|
| Live Y1 Forecast | `src/fsffl/product/p0_forecast_runtime.py`: embedded `P0_CURRENT_SOURCE_CSV` is required to have exactly 335 unique rows; source resolution accepts only frozen-table identity/provider refs. The production Shapley loader consumes preseason-baseline Y1 rows supplied by its authority loader. | Preserve the source/model authority. Build a candidate feature adapter from canonical player identity + point-in-time Forecast/source facts; retain source/model lineage and require a usable Y1 authority, otherwise a player-specific failure. |
| Y2/Y3 future-state Forecast | `src/fsffl/forecast/future_state_primitive.py` and `src/fsffl/product/p0_forecast_runtime.py` both resolve identities through frozen 335-row source maps and check position/Y1 parity. `src/fsffl/product/p0_future_forecast_provider.py` intersects P0-governed IDs with compatible Y1/league scoring evidence before materialization. Existing future-state models estimate out/depth/usable/starter/premium/elite probabilities and P0's D0/D1 path derives conditional production. | Generalize only the input/materialization boundary to score an explicitly requested subject through the unchanged fitted parameters; keep deterministic normalization against the frozen reference population and reject unsupported identity/position/scoring. First prove parity on all 335. |
| Current Intrinsic Y1–Y3 | `src/fsffl/product/private_beta_shapley_runtime.py` composes Y1 rows with the injected Future Forecast contract; its player universe is that contract's IDs. `src/fsffl/value/live_intrinsic_calendar.py` and `src/fsffl/value/shapley_intrinsic.py` calculate existing league-aware Shapley economics over that universe. Legacy `src/fsffl/value/intrinsic_runtime.py` likewise consumes supplied Y1 observations and does not itself require membership in the 335 table. | Expand the upstream candidate universe; do not change Current/Shapley math. Candidate set and exact State/team/model inputs must be fingerprinted so saved coverage cannot be reused across a different evaluation scope. |
| Y4–Y7 Forecast / Intrinsic | `src/fsffl/product/foundation4_shadow_inputs.py` loads a hash-checked gzip board with exactly 335 × 4 years × 4 policies. `src/fsffl/value/long_term_intrinsic.py` calculates the unchanged Shapley authority for the board IDs. The runtime package contains frozen predictions, not an inference API. `scripts/materialize_foundation4_current_long_horizon_board.py` invokes `route.fit_candidate(...)` to produce the current board. | **Critical first engineering gate:** recover/package the accepted inference scorer, feature transform, policy routing and residual bands from the exact accepted evidence, without fitting on new players or changing the chosen models. Replay all 335 rows within frozen tolerance before any out-of-core scoring. If this cannot be done without a new fit/research/model decision, stop for Management rather than retrain. |
| Y8+ terminal/tail | `src/fsffl/product/foundation4_shadow_inputs.py` requires exactly 335 terminal rows. `src/fsffl/value/career_tail.py` already exposes a fitted scorer over age, experience, current points, prior points and prior-missingness, with two supported model families, residual bands, and an exact lineup-capacity-signature check. | Reuse `CareerTailFeatures`/the fitted runtime only after producing point-in-time, scoring-coordinate-correct features for a candidate. Keep model-family spread separate from outcome bands. A missing current/prior value must remain missing with provenance, never be silently converted into an invented zero. |
| Career Forward aggregation | `src/fsffl/product/foundation4_career_forward_runtime.py` requires the component player-ID sets to equal Current's set and terminal features to have that same set. `src/fsffl/value/career_forward_intrinsic.py` independently enforces identical Current/Y4–Y7/tail cohorts and the accepted raw annual aggregation. | Extend coverage/status metadata and fingerprints, not the aggregation formula. Emit per-player estimate or typed authority failure; never publish a complete accounting status when any rostered player lacks authority. |

## Smallest reusable mechanism

Implement one **Career Coverage Subject Resolver + evidence/materialization adapter** at the Forecast/Foundation boundary, not a Dynasty-specific value model:

1. Resolve the deduplicated, position-checked subject set as frozen reference IDs ∪ exact-State rostered QB/RB/WR/TE IDs ∪ specifically requested acquisition candidates. Preserve canonical player ID, position, exact State, league/rules, team ownership where applicable, and request purpose.
2. Materialize a typed evidence packet from existing, point-in-time-authoritative sources: Y1 Forecast and scoring coordinate; prior seasons/history; age/experience; opportunity/participation; NFL attachment/status and injury/availability; prospect/career-trajectory evidence when governed; source/model/version and per-family coverage. Roster slot is not a feature or eligibility gate.
3. Score with unchanged, versioned accepted model parameters and existing Current, Y2/Y3, Y4–Y7, Y8+ and Shapley economics. Feature transforms, thresholds, missingness handling, reference percentiles, and calibration bands must be explicit and replayable. A coverage adapter may construct inputs, but may not learn coefficients from new candidates or use Market values.
4. Return a per-player authority record: `ready` with estimate, source/model provenance, evidence tier, confidence, and separate ordinary/model-authority uncertainty; or `unavailable` with a stable player-specific reason and missing evidence families. No silent omissions and no arbitrary-zero fallback.
5. Keep `accounting_subject_ids` separate from `valuation_candidate_ids`. A requested free agent is scored using the same league rules and accepted model family but is never added to a team room until the exact State roster shows acquisition. Candidate set is part of the valuation fingerprint; each request remains State/league/tenant fenced.

## Evidence tiers and current support

- **Tier 1 — direct governed evidence:** canonical identity/position plus authoritative, as-of-compatible Y1 forecast, model/scoring lineage, and the accepted future-horizon scorer inputs. Full estimate may be returned with the accepted evidence path.
- **Tier 2 — governed sparse/mixed evidence:** essential identity, position and age/experience resolve; some history/role/opportunity/availability/prospect inputs are missing. Score only if each accepted model explicitly supports those missingness indicators. Attach lower confidence and wider empirically supported uncertainty; never manufacture an observation.
- **Tier 3 — player-specific authority failure:** identity or position conflict; no eligible Y1 authority; essential model features cannot be constructed; candidate lies outside the accepted scorer's validated feature domain; or a required scoring/lineup-capacity authority is incompatible. Return a stable reason code and affected horizon/family. Do not exclude the rostered player from coverage reporting; do not score with Market or zero.

Current model limitations that must remain explicit:
- Existing state models use current/prior production, age/experience, current football state, source role/games/opportunity and frozen reference percentiles. Some coverage terms are hard-coded uncovered, and the feature set does not currently include a governed injury input or incumbent-depth-chart relationship. Thus injured/blocked cases are not automatically distinguished from ability merely because canonical state has such evidence.
- Tax/bench/IR slot does not enter the forecast. Those slots must not be used as proxy features; taxi rookies require football/prospect evidence and supported model inputs.
- Veteran/no-current-team cases may use supported age/experience/history and attachment/availability evidence only if accepted inference features include them. Do not treat no team as zero production or automatic exclusion.
- Intrinsic v1 can label conservative Y2/Y3 carry-forward as low strength, but that alone is not the required governed wider uncertainty for every sparse candidate.
- Current Y1 and the Y4–Y7 board are existing cohort/materialization boundaries. Y4–Y7 inference is the key feasibility gate; no user-facing extension starts before exact scorer provenance and parity are established.

## On-demand free-agent semantics

A free-agent candidate enters valuation only through an identified Market/Search/Waiver/Opportunity/Trade/What-If or explicit lookup request. Discovery context may identify its player ID; Market value, percentile or rank is not a Career feature. The resolver then uses canonical State/player identity and the same upstream scoring/evidence requirements. The output is candidate-scoped, exact-State/fingerprint-bound, and does not write a roster entry, team-room row, or team asset count. If later acquired, roster membership comes only from a new/exact League State and deduplicates the player into accounting coverage. Unknown/unresolved Sleeper IDs fail per player; no full-database materialization.

## Bounded PR sequence

**PR 0 — this checkpoint (complete).** Correct the issue's 22-vs-25 error and store this trace/plan in operations docs. Documentation-only; no model/test/deploy change.

**PR 1 — scorer authority and parity gate.** Trace accepted P0/state and Y4–Y7 fitted artifacts to their exact source/training artifact hashes, transforms, coefficient/policy/uncertainty objects and inference code. Package a deterministic scorer without new fitting. Add 335-core parity golden tests and artifact/hash checks. Stop if exact accepted scorer cannot be reconstructed from retained evidence or parity is outside existing tolerances.

**PR 2 — subject resolver + rostered coverage.** Add the typed resolver/feature packet, candidate coverage reports, per-player provenance/confidence/uncertainty/failure contract, and same-State model scoring through unchanged authorities. Integrate Current, Y2/Y3, Y4–Y7 and terminal as supported. Keep #370 untouched and fail closed on player failures. Add rostered archetype regressions: veteran, injured established, incumbent-blocked young, taxi rookie, low-production developmental, older/no-current-NFL-team, sparse-evidence. Audit the exact preserved 25 as a regression fixture, not as current production truth.

**PR 3 — on-demand acquisition candidates.** Reuse the same resolver/scorers for explicit relevant free-agent IDs; expose candidate valuation to the existing discovery/lookup consumer boundary. Verify no room/accounting insertion before acquisition, no tenant/State leakage, and Market-only discovery does not feed Career numbers.

**PR 4 — integration and stable merge gate.** Validate Current + Career Forward exact cohort semantics and #370's roster completeness invariant, focused tests first, then one full suite at stable PR head per the current operating protocol. Merge/deploy only after scorer parity, all archetype/failure regressions, exact-State/tenant isolation, preserved economics and output status are verified.

## Regression matrix / acceptance

Each regression should assert values are finite and provenance/uncertainty are present when `ready`, or a documented player-specific failure when not yet governable; never assert a forced positive result from sparse evidence.

| Archetype | Required feature path / safety check |
|---|---|
| Veteran | Age/experience + prior production; retain valid Y1 and long-horizon evidence. |
| Injured established player | Injury/availability evidence stays distinct from ability; low current output cannot be mechanically extrapolated. |
| Incumbent-blocked young player | Role/opportunity and prospect/career evidence, not fantasy roster slot; no false zero from low production. |
| Taxi rookie | Roster membership cannot exclude; governed prospect/age/experience path or explicit missing-authority reason. |
| Low-production developmental player | Future-state probabilities + conditional production; sparse inputs widen uncertainty or fail explicitly. |
| Older/no-current-NFL-team player | History/age/attachment features; no membership exclusion or market substitution. |
| Sparse-evidence player | Coverage indicators and explicit evidence tier; wider supported uncertainty or player-specific failure, never silent zero. |
| Acquisition-relevant free agent | Candidate valuation available on request but absent from team room/accounting until State shows acquisition. |

## Resume instructions

Resume from current GitHub main and read [Current Operations](../CURRENT_OPERATIONS.md), this checkpoint, Issue #405, and the referenced accepted Forecast/Foundation 4 artifacts. Do not inspect or modify stale local clones. Start with PR 1's accepted-artifact/scorer provenance gate—not code changes to #370 or publication/lifecycle. No full suite is needed for this documentation checkpoint. At the PR 1 stable merge gate, use focused validation during development and one full suite only once.
