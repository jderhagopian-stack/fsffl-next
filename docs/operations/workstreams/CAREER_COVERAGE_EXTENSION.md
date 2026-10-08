# Career Coverage Extension — Issue #405 implementation checkpoint

Updated: 2026-10-07  
Status: **MANAGEMENT AUTHORIZED — reuse accepted deterministic Y4–Y7 pipeline + dynamic production-universe extension; implementation not yet resumed**  
Authority: [Issue #405](https://github.com/jderhagopian-stack/fsffl-next/issues/405) and [Current Operations](../CURRENT_OPERATIONS.md). This is a separate Career/Foundation 4 workstream, not Architecture Recovery.

## Decision and scope

The frozen 335-player cohort remains the validated calibration/reference cohort, but cannot remain the production valuation ceiling.

For an exact evaluated League State, the accounting population is every rostered QB/RB/WR/TE, regardless of starter, bench, IR or taxi slot. Each must produce a governed Career-forward estimate or a player-specific model-authority failure. A failure remains visible and keeps #370's existing completeness gate closed; it is never converted to zero or hidden by a slot filter.

The 335-player set remains the frozen calibration/reference cohort, but production coverage is broader.

The production populations are:
- **reference cohort:** the accepted frozen 335 used for parity, normalization and model governance;
- **accounting population:** every exact-State rostered QB/RB/WR/TE, regardless of starter/bench/IR/taxi;
- **league decision universe:** the accounting population plus a broad, precomputed fantasy-relevant waiver/free-agent cohort so Career evidence is present before a user makes an add/waiver decision;
- **extended universe:** unusual/deep candidates scored on demand when identified by Explore/Search/Waiver/Trade/What-If/explicit lookup.

An unrostered candidate may be valued without being inserted into any team's room/accounting. The waiver cohort must be selected by an explicit governed football/eligibility contract rather than an arbitrary top-N cutoff. Whole-provider-database materialization remains unnecessary: the goal is comprehensive **fantasy-relevant decision coverage**, not scoring every Sleeper identity.

Market/Search/Waiver/Opportunity/Trade/What-If/explicit lookup may identify a candidate or help establish decision relevance. Market remains a separate coordinate and is not a numeric Career Intrinsic input.

### Scalable refresh/materialization contract
Dynamic does **not** mean recompute everything continuously.

The target refresh design is:

1. **Cheap change detection first.** Provider synchronization / Refresh Intelligence determines whether any Career-relevant evidence changed. Opening Franchise/League/Explore/Trade must not itself launch heavy Career work.
2. **Separate stable model authority from mutable player evidence.** If the accepted Y4–Y7 historical-training/model/route fingerprint is unchanged, reuse the fitted/model authority for in-season scoring. Do not refit the historical model merely because current player evidence changed. A parity-safe packaged/cached fitted representation is permitted as an implementation optimization if it is proven identical to the accepted deterministic pipeline.
3. **Batch current evidence.** Build the roster + broad waiver decision-universe feature/evidence table once per publication generation. Cohort-relative transforms/normalizations, where the accepted model requires them, are computed consistently across that governed batch rather than independently per request.
4. **Selective invalidation.** Compare player/material dependency fingerprints. Reuse unchanged player projections; recompute changed/new subjects. Do not rebuild historical inputs or unchanged horizons solely because another player's evidence changed unless the accepted math has a global dependency.
5. **Coalesce global downstream work.** Some Value/Shapley/rank outputs are league/cohort dependent. If any relevant upstream subject changed, recompute those global downstream artifacts **once** for the new publication after the changed player-level evidence is ready—not once per transaction, player, or browser request.
6. **Prewarm the ordinary waiver universe.** Broad fantasy-relevant free agents are materialized with the publication so waiver decisions are immediately informed. Deep/unusual long-tail candidates may be scored on demand and cached under the exact evidence/model fingerprint.
7. **Full rematerialization is exceptional but legitimate.** New evaluation season, promoted model/version, changed historical training set, changed league scoring/lineup authority where required by the model, or an incompatible normalization/reference coordinate can require a full rebuild.
8. **Last-good stays usable.** While a new Career publication is building, serve the prior compatible point-in-time Career artifact with truthful stale/updating status rather than blocking the product.
9. **Measure cost as an acceptance condition.** Record changed-subject count, model-fit reuse/refit count, player-evidence materialization time, global downstream recompute time, peak RSS, and total publication latency. Validate both a normal 12-team league and a larger/deeper roster + waiver universe so the design is demonstrably scalable.

This contract deliberately avoids a fixed weekly/nightly recomputation requirement. Freshness is tied to materially changed governed evidence and successful publication. A low-priority periodic integrity sweep may be added later as an operational backstop, but it is not the source of truth.

### Multi-league / commercial-scale requirement
The current private beta is validation evidence, not the computational unit of the future product. #405 must avoid an architecture where 1,000 or 10,000 leagues cause 1,000 or 10,000 copies of work whose inputs are actually shared.

Before implementation chooses cache/materialization boundaries, classify each Career dependency by the **widest safe semantic scope**:
- **provider/global evidence:** canonical NFL/player facts that are identical across leagues;
- **model/training authority:** accepted fitted model/policy objects and historical-training fingerprints that must be reused rather than fitted per league;
- **scoring/rules signature:** derived player projections/materializations that may be shareable by leagues with identical relevant scoring semantics;
- **lineup/team-count signature:** Value/Shapley inputs that depend on lineup-capacity economics but not on a particular owner's roster;
- **exact league State:** only facts that truly vary with league membership/rules/availability/ownership;
- **team/user context:** downstream Decision/Search/Presentation context, never folded back into universal Career authority.

Required properties:
1. No per-league historical model fitting when model/training inputs are identical.
2. No duplicate provider ingest or canonical player-evidence construction per league.
3. Cache/artifact keys must use semantic dependency fingerprints, not league ID as an unnecessary partition key. Tenant-private State must still remain isolated.
4. Leagues sharing the same safe dependency signature should reuse the same upstream artifact; league-specific downstream artifacts may reference it.
5. Provider-wide evidence changes should be coalesced into shared upstream refresh work, then fan out only to affected league-specific downstream publications.
6. Background work needs bounded concurrency/backpressure so a Sunday/waiver/news burst cannot create an unbounded thundering herd across leagues.
7. Last-good intelligence remains available while queued refresh work catches up; freshness age/status must remain truthful.
8. Acceptance must include a **resource-proportionate scale model**, not a brute-force 1,000/10,000-league execution. Measure real per-scope costs on the current beta and a bounded synthetic/representative fan-out, verify cache/deduplication/cardinality behavior, and project 1,000- and 10,000-league CPU/memory/work envelopes. Demonstrate that expensive shared stages grow primarily with unique evidence/rules signatures and changed subjects—not linearly with raw league count when reuse is mathematically valid. Do not exceed current compute/memory budgets merely to create load-test volume.


### Dynamic point-in-time requirement
Coverage and freshness are one production contract. Career Intrinsic must not become a season-long static table merely because its model/policy is frozen.

- The **model/policy authority** may be frozen, versioned and changed only through governance.
- The **player evidence coordinate** is point-in-time and may change as governed football evidence changes: current Forecast, production/participation/opportunity, attachment/status, injury/availability where supported, age/experience at the appropriate boundary, and other accepted model inputs.
- Material evidence changes must change the relevant dependency fingerprint and permit selective rematerialization of affected Career outputs under the same accepted authority.
- A new season must establish a new evaluation-season coordinate and rematerialize Career evidence; a 2026 board may never silently answer a 2027 request.
- Prior materializations should remain durable as historical point-in-time snapshots rather than being overwritten as though they had never existed.
- This does not require request-time fitting or a full rebuild on every browser visit. Refresh should be driven by governed evidence change / explicit intelligence refresh and reuse unchanged artifacts when fingerprints remain compatible.

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
| Y4–Y7 Forecast / Intrinsic | `src/fsffl/product/foundation4_shadow_inputs.py` loads a hash-checked gzip board with exactly 335 × 4 years × 4 policies. `src/fsffl/value/long_term_intrinsic.py` calculates the unchanged Shapley authority for the board IDs. The runtime package contains frozen predictions, while the accepted deterministic fitting/materialization methodology is preserved in Git and invoked by `scripts/materialize_foundation4_current_long_horizon_board.py` through `route.fit_candidate(...)`. | **Critical first engineering gate:** reuse the exact accepted deterministic pipeline and replay all 335 rows within frozen tolerance, then generalize only the subject/evidence/materialization boundary. A parity-safe packaged fitted representation may be introduced as an optimization, but no scorer rediscovery, new model search, or current-player fitting/tuning is authorized. |
| Y8+ terminal/tail | `src/fsffl/product/foundation4_shadow_inputs.py` requires exactly 335 terminal rows. `src/fsffl/value/career_tail.py` already exposes a fitted scorer over age, experience, current points, prior points and prior-missingness, with two supported model families, residual bands, and an exact lineup-capacity-signature check. | Reuse `CareerTailFeatures`/the fitted runtime only after producing point-in-time, scoring-coordinate-correct features for a candidate. Keep model-family spread separate from outcome bands. A missing current/prior value must remain missing with provenance, never be silently converted into an invented zero. |
| Career Forward aggregation | `src/fsffl/product/foundation4_career_forward_runtime.py` requires the component player-ID sets to equal Current's set and terminal features to have that same set. `src/fsffl/value/career_forward_intrinsic.py` independently enforces identical Current/Y4–Y7/tail cohorts and the accepted raw annual aggregation. | Extend coverage/status metadata and fingerprints, not the aggregation formula. Emit per-player estimate or typed authority failure; never publish a complete accounting status when any rostered player lacks authority. |

## Management correction — accepted Y4–Y7 authority is pipeline-defined

The earlier audit correctly observed that the retained route artifact contains predictions/metrics/route decisions rather than a standalone serialized fitted estimator. It was incorrect to infer from that fact that the accepted scorer methodology was lost.

The accepted design is reproducible and pipeline-defined:

- corrected research code is durably preserved at Git commit `be2541a496227b33c12c755f576843dc4ab5a0bb`;
- `scripts/run_intrinsic_cell_routing_validation.py` defines `fit_candidate(...)`, which selects the frozen candidate architecture and fits it against governed historical rows prior to the evaluation season;
- `scripts/run_intrinsic_comprehensive_development.py` contains the frozen feature sets/model implementations and deterministic seed `20260926`;
- accepted Foundation 4 workflow run `37096263982` / workflow `.github/workflows/foundation4-current-long-horizon-board.yml` explicitly restores those two programs from the accepted commit, restores governed historical and route artifacts, and runs the materializer;
- the materializer calls `route.fit_candidate(...)` for the frozen policy candidates and current evaluation rows, then freezes the resulting season board;
- runtime intentionally consumes that frozen season board rather than fitting on HTTP requests.

Therefore no reverse-engineering or invention of a replacement scorer is authorized or needed. The required gate is to **reuse the exact accepted deterministic pipeline** and prove it reproduces the frozen 335 reference board within governed tolerance before broadening its subject universe.

Required constraints:
1. Preserve the remaining accepted historical/route artifacts and their hashes/provenance before retention expiry.
2. Reuse the exact accepted code, historical evidence, frozen candidate/route policy, seeds/settings, feature transforms and scoring coordinate.
3. The 25 missing rostered players, waiver candidates and other out-of-core subjects must not participate in model-family selection, route selection or tuning.
4. Do not search alternative model families, optimize for improved results, or change Career economics.
5. Reproduce the frozen 335 reference outputs within the governed/frozen tolerance before any out-of-core materialization is promoted.
6. If parity fails, stop and return to Management. Do not compensate with coefficient guessing, interpolation, Market values or a replacement model.
7. After parity, make the existing pipeline reusable for the broader subject/evidence boundary; whether implementation chooses durable packaged fitted objects or deterministic batch fitting is an engineering choice only if outputs/authority remain identical.

The current production assets are explicitly 2026-season scoped. That is a current implementation boundary, not the intended product semantics. The #405 architecture must make annual rollover and evidence-driven in-season rematerialization possible now; only the exact cadence/trigger optimization may remain an operational follow-up.


## Smallest reusable mechanism

Implement one **Career Coverage Subject Resolver + evidence/materialization adapter** at the Forecast/Foundation boundary, not a Dynasty-specific value model:

1. Resolve the deduplicated, position-checked subject set as frozen reference IDs ∪ exact-State rostered QB/RB/WR/TE IDs ∪ governed fantasy-relevant waiver/free-agent IDs ∪ specifically requested long-tail acquisition candidates. Preserve canonical player ID, position, exact State, league/rules, team ownership where applicable, waiver-universe eligibility/provenance, and request purpose.
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

## Waiver/free-agent semantics

The user must not need to identify a player manually before Career evidence exists for ordinary waiver decisions.

At each applicable league publication, materialize Career coverage for a **broad governed fantasy-relevant waiver/free-agent cohort** in addition to every rostered QB/RB/WR/TE. Define this cohort through explicit football/eligibility evidence supported by existing authority (for example canonical identity/position, NFL attachment/status, usable Forecast/current-or-prior participation/opportunity, or governed prospect evidence) rather than an arbitrary top-N rank. The exact eligibility rule must be documented, deterministic, State/as-of aware, and testable before activation.

Explore/Search/Waiver/Opportunity may expose these precomputed candidates. Market value, percentile or rank may help identify decision relevance but is not a Career feature.

The long tail remains on demand: Trade/What-If/explicit lookup or other discovery may request an eligible out-of-cohort player through the same scorer and evidence adapter. Neither precomputed nor on-demand free agents write a roster entry, team-room row or team asset count. If later acquired, roster membership comes only from the new/exact League State and the already-scored player deduplicates into accounting coverage. Unknown/unresolved identities fail per player.

Whole-Sleeper-database materialization is not required; broad fantasy-relevant waiver coverage is.

## Bounded PR sequence

**PR 0 — this checkpoint (complete).** Correct the issue's 22-vs-25 error and store this trace/plan in operations docs. Documentation-only; no model/test/deploy change.

**PR 1 — accepted-pipeline preservation and parity gate (authorized).** Preserve the remaining historical/route evidence before retention expiry. Reuse the exact accepted Git-pinned development/route programs and governed historical inputs to reproduce the frozen 335 Y4–Y7 board through the existing fit-on-materialization path. No out-of-core player may enter model-family/route selection or tuning. If all 335 reference outputs replay within governed tolerance, checkpoint the exact pipeline identity/provenance and the smallest reusable production seam for broader subjects. If parity fails, stop for Management.

**PR 2 — subject resolver + dynamic evidence/materialization contract + rostered coverage.** Add the typed resolver/feature packet, candidate coverage reports, per-player provenance/confidence/uncertainty/failure contract, and same-State model scoring through unchanged authorities. Make the subject/evidence fingerprint include every material accepted player-evidence dependency so a changed football input invalidates/rematerializes the affected Career output while unchanged evidence remains reusable. Establish an evaluation-season boundary that cannot reuse a prior-season board. Integrate Current, Y2/Y3, Y4–Y7 and terminal as supported. Keep #370 untouched and fail closed on player failures. Add rostered archetype regressions: veteran, injured established, incumbent-blocked young, taxi rookie, low-production developmental, older/no-current-NFL-team, sparse-evidence. Audit the exact preserved 25 as a regression fixture, not as current production truth.

**PR 3 — broad league waiver decision universe.** Define and document the deterministic governed fantasy-relevant free-agent eligibility contract; precompute/materialize Career coverage for that waiver universe alongside rostered coverage. Verify that ordinary waiver candidates surface Career evidence before acquisition, that Market signals do not enter Career scoring, and that no free agent is inserted into team accounting before the exact State shows acquisition.

**PR 4 — long-tail on-demand candidates.** Reuse the same resolver/scorers for unusual/deep explicitly relevant free-agent IDs outside the precomputed waiver cohort. Verify exact-State/tenant fencing, cache/fingerprint correctness, player-specific authority failures, and deduplication when a later State shows acquisition.

**PR 5 — integration and stable merge gate.** Validate Current + Career Forward cohort semantics, broad waiver coverage and #370's roster completeness invariant, focused tests first, then one full suite at the stable PR head per the current operating protocol. Merge/deploy only after scorer parity, roster + waiver-universe archetype/failure regressions, exact-State/tenant isolation, preserved economics and output status are verified.

## Dynamic freshness acceptance

Before #405 is complete:
- a material governed player-evidence change must produce a new relevant input fingerprint and a new Career materialization for that subject/universe;
- an unchanged evidence coordinate must reuse the compatible artifact rather than recomputing solely because a page was opened;
- a season change must reject prior-season Career materialization and build/require the new evaluation-season coordinate;
- prior point-in-time Career outputs must remain auditable/preservable for historical reconstruction;
- broad waiver candidates and rostered players must follow the same freshness/season semantics;
- refresh behavior must preserve the accepted model/policy authority and may not turn changing evidence into model retuning.

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

## Historical PR1 no-fit interpretation (superseded 2026-10-07)

**Historical outcome, no longer the governing PR1 disposition:** this read-only attempt stopped because it interpreted the absence of a serialized scorer as a prohibition on rerunning the accepted deterministic fit-on-materialization pipeline. Management has explicitly corrected that interpretation. Its artifact provenance and hashes remain valid, but its no-fit blocker and resume gate are superseded by the approved reuse/replay requirement above.

Verified from the exact accepted workflow and downloaded artifact manifests:

- Current production source is main `cbdd559848e57d096977b4863e5508ad6db8a637`.
- The accepted Y4–Y7 board was generated by workflow run `37096263982`, head `4e6aaa4289924ccc1e050d2ebd1d59d1277276e7`. Its artifact is `11263913850`, `foundation4-current-long-horizon-board`, SHA-256 `6a79e2d793403c128c1c34ee3ffb044aba67f873ec92b8c61a702d26c06c1b22` (expires 2026-10-17).
- The archive contains the 335-player Y4–Y7 CSV/gzip board, 335-player terminal feature CSV/gzip, board summary, FSFFL rolling policy cell metrics and predictions, terminal-tail evidence/closeout/rolling validation/final-holdout predictions, and the Y8+ runtime package. It contains **no Y4–Y7 serialized estimator, coefficients, candidate feature-transform/scoring package, or inference API**.
- The accepted route evidence is workflow run `36271080037`, source head `be2541a496227b33c12c755f576843dc4ab5a0bb`, artifact `10916355135`, SHA-256 `63520ddb60a8ed12724fa21e8d276c4e3e7d5587162aade92ba7afaa3796ced2` (expires 2026-10-10). Its archive contains routing decisions, route weights, candidate-selection scores, rolling/outer-fold predictions and metrics, interpretation, and validation result; no fitted scorer object.
- Exact route/policy source files at those accepted heads: `scripts/run_intrinsic_cell_routing_validation.py` blob `f932f07c9cb29b3c07352d48a928d0b190562a29`; `scripts/run_intrinsic_comprehensive_development.py` blob `ebb472514ece122bbdbabfe60cca991e5941ae1b`; policy freeze `CELL_ROUTING_POLICY_FREEZE.json` blob `beded6dd776719c19c7323d4e8fa5e4d4d81b0c0`; current FSFFL materializer `scripts/materialize_foundation4_fsffl_coordinate.py` blob `2b31040b2c38215636981ac7ad0744aaf759acee`.
- The materialization workflow `.github/workflows/foundation4-current-long-horizon-board.yml` restores the development and route programs from `be2541a496227b33c12c755f576843dc4ab5a0bb`, supplies the exact panel/term/route artifacts and frozen policy, then runs the materializer. In that script, `candidate_prediction()` calls `route.fit_candidate(...)`; the fixed-route bank and current-policy rows call this path to produce the accepted 335-player board. The accepted summary's `model_refit_at_runtime=false` describes production runtime consuming the frozen board; it does not mean a scorer object was retained for new-player inference.
- Frozen board semantic hash: `3caddc5c33be83088eaca30d8c1ac7031022f08668a031a0a3b08616aed773c2`. Frozen Y4–Y7 authority-map hash: `487555fac2e5fd0823c6a70d29b1c1e60fbf2adc0e1bb8140f9f43e6ee0e9e00`. Exact extracted-file SHA-256s from the accepted archives: board CSV `f04547d3fae97420a12c13ff2f15010c9c54ec5b3a6af5ccd68927774aa12484`; cell-metrics CSV (the per-position/year/policy `mean_q80`/`mean_q90` bands) `ed37858d1e1a474d4ccabc4a160a239d3461046e3e9448493a816f0360b00b7c`; board summary `50c46c0a9ae6f618e3665bcde8f7bdf21dc9b8c0bead00ca0b98735b38ebb546`; `CURRENT_RESEARCH_ROUTE.csv` `313e5f0459bf9f7c85fe15b7c5a37635dc4e6eca70c6c661cd4d55517a238d6c`; `ROLLING_VALIDATION_RESULT.json` `140651374f1a13529895b3df2bc174a08a5f612ba8a1749cda211e8971967435`. Residual bands exist in the accepted cell-metrics artifact, but coefficients plus the complete inference/routing object needed to recompute a candidate's four policy forecasts are absent.
- Exact scoring/feature pipeline: FSFFL historical points are `nflverse standard + 0.5 × receptions + passing_interceptions + fumbles_lost`, with the transformed coordinate assigned to the forecast fields; `build_current` applies `dev.merge_lags`, `dev.add_engineered_features`, and `dev.merge_trajectory`, then restores frozen age/experience. The route builder's input transform and model code are the exact two accepted scripts above.
- Exact accepted candidate/policy semantics: the policy-freeze JSON identifies incumbent `specialist|forecast10|two_part_ridge`, shared anchor `global_continuous|football_plus|two_part_ridge`, the per-position/horizon specialist shortlists, and frozen rolling protocol; its blob SHA is `beded6dd776719c19c7323d4e8fa5e4d4d81b0c0`. `CURRENT_RESEARCH_ROUTE.csv` freezes per-cell hard candidate and soft weights. Materialization emits four policy boards: baseline (incumbent), hard_router (cell candidate), soft_stack (cell-specific weighted top three), and blanket_75_25 (75% prior specialist + 25% shared anchor). The Foundation 4 authority map selects the accepted policies by position/year. All exact row-level weights and numeric q80/q90 bands are integrity-bound to the extracted-file hashes above and the enclosing artifact SHA-256s.
- Re-running `fit_candidate` against retained historical inputs would fit models again; that is expressly prohibited by this PR1 directive. The frozen predictions and policy scores cannot determine unique coefficients or extrapolate another player's forecast. Interpolation, coefficient guessing, and a replacement model are not valid recovery paths.

**Exact blocker:** accepted Y4–Y7 authority was promoted as a frozen 335-player prediction board and its provenance/uncertainty, while the deterministic inference scorer/model objects were not retained. A candidate player's policy-specific Y4–Y7 values cannot be computed and parity cannot be demonstrated without fitting or a new model-authority decision.

**Resume gate:** Management must decide whether to authorize a new bounded authority step to recover/reproduce the accepted fitted objects (which may require a fit, therefore conflicts with the current prohibition), or accept that PR1 cannot proceed under the no-fit constraint. Until then, do not edit runtime/scoring code or start PR2. Existing P0 Y2/Y3 and Career-tail fitted runtimes do not close this Y4–Y7 gap.

Artifact-retention note: the routing artifact expires 2026-10-10 and current-board artifact expires 2026-10-17. The archive contents were inspected during this tranche; no local repository clone was used.

## Resume instructions

Resume from current GitHub main and read [Current Operations](../CURRENT_OPERATIONS.md), this checkpoint, Issue #405, and the referenced accepted Forecast/Foundation 4 artifacts. Do not inspect or modify stale local clones. Start with PR 1's accepted-artifact/scorer provenance gate—not code changes to #370 or publication/lifecycle. No full suite is needed for this documentation checkpoint. At the PR 1 stable merge gate, use focused validation during development and one full suite only once.

## PR1 resumed execution checkpoint — 2026-10-07 21:40 ET

Status: **ACTIVE — PR1 accepted-artifact preservation and deterministic frozen-335 replay; parity not yet established.** This checkpoint supersedes the prior no-fit stopping conclusion, **not** its factual artifact/source evidence. Model-family/route selection remains closed. Rerunning the accepted frozen historical fit is authorized solely to materialize the accepted 2026 reference pipeline; missing rostered/waiver players never enter training/route tuning.

- Verified GitHub main at start: `6649d9d547a3d424580588233c3b2d1774b4d938` (2026-10-07 21:26 ET), including global multi-league scale invariant #428.
- Execution branch: `work/career-coverage-pr1-parity-20261007` from that exact main.
- Draft PR: [#429](https://github.com/jderhagopian-stack/fsffl-next/pull/429); first replay workflow head `9ef844ff33f40b977742c77276f4f9bb222c19a3`.
- Dedicated once-per-PR1-code-change [replay run 37714107824](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37714107824) has passed archive/provenance stages and is running replay at this checkpoint. It does **not** run for documentation-only pushes.
- Artifacts reacquired from GitHub before expiration: terminal/historical package `10899387479` (ZIP SHA-256 `ea72f312148f01b8066419e8f12cb3a04a4dbbd99fd6e0b7dc975c65cc2446b5`), panel `10912862252` (`6dd664b632f4897f286a99794e10df29be21bf8c6cae70e526ea807470fdcb0e`), route `10916355135` (`63520ddb60a8ed12724fa21e8d276c4e3e7d5587162aade92ba7afaa3796ced2`), and reference board `11263913850` (`6a79e2d793403c128c1c34ee3ffb044aba67f873ec92b8c61a702d26c06c1b22`). All four downloaded ZIP hashes locally verified; workflow independently re-verifies before preservation.
- Durable archive plan: workflow creates GitHub release tag `career-405-accepted-research-evidence-20261007` at the frozen pre-work main SHA and attaches **all four exact ZIPs and SHA256SUMS**. **Verified durable:** GitHub release [career-405-accepted-research-evidence-20261007](https://github.com/jderhagopian-stack/fsffl-next/releases/tag/career-405-accepted-research-evidence-20261007), release ID `406321196`, contains all four hash-verified ZIP archives (20,765,419 / 3,902,644 / 809,045 / 1,100,940 bytes) and SHA256SUMS. The preserving run successfully completed the recover, archive, and immutable-source verification stages; replay parity is still in progress.
- Accepted source pins: development blob `ebb472514ece122bbdbabfe60cca991e5941ae1b`, route blob `f932f07c9cb29b3c07352d48a928d0b190562a29`, FSFFL materializer blob `2b31040b2c38215636981ac7ad0744aaf759acee`, policy blob `beded6dd776719c19c7323d4e8fa5e4d4d81b0c0`. Replay is the accepted run `37096263982` workflow command, Python 3.11, same declared dependencies, frozen 2026 board and unchanged FSFFL scoring transform.
- Comparison: 5,360 row-keyed policy×year predictions covering **335** exact players across Y4–Y7, central forecasts plus q80/q90, every per-cell uncertainty metric, **335** terminal feature rows, and exact board metadata. Fail-closed numeric replay tolerance proposed at `abs_tol=1e-8, rel_tol=1e-10` (strict deterministic float tolerance, not model-recalibration permission); categorical provenance must be exact. Report includes maximum numeric residual and replay peak RSS/runtime.
- No model/scoring/runtime/page/State changes are in this PR; #370 remains untouched. PR2–PR5 **remain blocked** pending a genuinely successful replay, immutable input archive verification, stable-head acceptance and final PR1 checkpoint.
- After accepted parity: identify the smallest reusable fitted scorer and point-in-time evidence/materialization seam; downstream dynamic evidence, waiver/long-tail, shared model fingerprints, cross-league deduplication and 1k/10k bounded resource projections remain the **approved #405 gates**, not optional future research. Never fit the 25 missing or broad waiver player rows, select routes anew, or force a guess on an ungovernable player.

Next action: inspect run `37714107824` and release asset verification; if replay fails, diagnose only environment/pipeline fidelity and preserve exact evidence, then stop for Management if accepted-parity cannot be met without changing frozen authority. Do not promote PR2 on a queued or failed parity check.

### PR1 first replay result and exact-environment correction — 2026-10-07 21:50 ET

- [Run 37714107824](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37714107824) **failed parity** after successful preservation/source verification and successful historical FSFFL materialization. No new subjects entered fitting. Reference comparison reported **10,227 numeric board mismatches** at the intentionally strict `1e-8` absolute / `1e-10` relative comparison, with maximum absolute difference `0.04414185823849692`. Representative current forecast predictions differed ~`4e-6`, residual q80/q90 values by roughly `0.001–0.014`. This is **not** accepted numerical parity.
- Diagnostic replay artifact `11523486083`: [download via Actions](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37714107824/artifacts/11523486083). Replay resource cost: elapsed `8:11.41`, peak RSS `584872 KB` on GitHub Actions runner; do not confuse this with hosted Render budget.
- **Environment mismatch proven:** accepted run `37096263982` installed NumPy `2.4.6`, SciPy `1.17.1`, pandas `3.0.6`, scikit-learn `1.9.1` on Python `3.11`. Unpinned PR1 replay installed NumPy `2.5.3`, SciPy `1.18.1`, pandas `3.0.6`, scikit-learn `1.9.1`. These versions are extracted from actual successful pip installation logs; different floating results cannot currently be attributed to model-policy drift.
- Narrow action: workflow commit `1eff9d70708575095a626268abe306af8bdf8659` pins the **exact accepted numerical stack**; [run 37714917669](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37714917669) is the corrective deterministic replay. No model/seed/route/history/input artifact or tolerance changes. Archive release remains complete and durable.
- **Gate remains CLOSED** until pinned replay passes or a documented true discrepancy is escalated. Do not start PR2 or retune. If the exact-environment replay still differs, report the exhaustive numerical residuals and the earliest original-authority disagreement to Management rather than guessing coefficients or relaxing acceptance.


### Historical 25-player identity-fixture provenance check

The 2026-10-06 Management read-only Dynasty/Career audit PDF enumerates **all 25 missing players by name, position and roster slot** (5 QB, 8 RB, 10 WR, 2 TE), and Issue #405 now preserves that audit list explicitly. Contrary to an older issue summary, **neither the memo nor the issue exposes the exact canonical Sleeper player IDs**. The executable PR2 historical regression must resolve the IDs from the exact archived League State hash `606ba3cd0acf427f6724665546dfcbcce0013e593abb658277466c2725b7d2d3`; names are audit evidence, not an identity substitution. Do not infer IDs via player-name matching against a newer State or treat the historical 25 as live 2026 coverage truth. No production State was mutated during PR1.

### PR1 second replay / Python-interpreter fidelity correction — 2026-10-07 22:00 ET

- [Run 37714917669](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37714917669), artifact `11523786224`, passed archive/source verification and materialization, but still produced **exactly the same 10,227 mismatches / max absolute 0.04414185823849692** under pinned NumPy 2.4.6 / SciPy 1.17.1. This **does not yet establish accepted-pipeline parity**.
- Source-log diagnosis: the original accepted workflow explicitly ran `actions/setup-python@v5` with `python-version: '3.11'`, and installed cp311 wheels. Our replay YAML accidentally omitted setup-python and installed **cp312** wheels (Python 3.12), proven by pip install logs; the changed numeric packages alone therefore did not reproduce the original interpreter/ABI or floating arithmetic.
- Exact corrective step: workflow commit `f96a9dad6e8b0ff20b33cc0d9798478df888d885` restores `actions/setup-python@v5` to Python **3.11** and asserts the interpreter, preserving all four accepted numerical library pins, original source/inputs and the original strict comparison. [Run 37715717925](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37715717925) is the **first** full original-Python+numeric-stack fidelity replay.
- Archive remains durable. PR2–PR5 are not promoted; if this truly matching environment still disagrees, **stop at the Management parity gate** with no numerical tolerance relaxation, model substitution or unapproved route refit.

## PR1 parity forensic diagnosis — 2026-10-07 / completed Python 3.11 replay

**Disposition: MANAGEMENT GATE — PR1 numeric parity NOT accepted. No blind replay, no tolerance change, no model/route/economic/runtime modification, and no PR2 promotion.** This supersedes the pending-run status of the immediately preceding checkpoint, not its preserved audit or source hashes.

### Exact execution and retained evidence

- Accepted run: [37096263982](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37096263982), source head `4e6aaa4289924ccc1e050d2ebd1d59d1277276e7`, reference artifact `11263913850`; route run `36271080037` / artifact `10916355135`; original accepted research code commit `be2541a496227b33c12c755f576843dc4ab5a0bb`.
- Diagnosis: [first replay 37714107824](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37714107824) artifact `11523486083`; [numerical-dependency-pinned replay 37714917669](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37714917669) artifact `11523786224`; [original Python 3.11 + original library versions replay 37715717925](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37715717925) artifact `11524051845`.
- All original input/history, route, accepted frozen-board ZIPs, plus **all three replay ZIPs and two SHA256 manifests** are now durably preserved in [release career-405-accepted-research-evidence-20261007](https://github.com/jderhagopian-stack/fsffl-next/releases/tag/career-405-accepted-research-evidence-20261007), release ID `406321196`. Archive-only workflow [37720102876](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37720102876) succeeded. No materializer/fitter ran in the archive-only workflow.
- Accepted reference board CSV SHA256: `f04547d3fae97420a12c13ff2f15010c9c54ec5b3a6af5ccd68927774aa12484`. **Each of the three replay board CSVs is byte-identical to the other replays**, SHA256 `fd66a62f2c9fd71c6be00b980279af53446e980bba435a3bb07fd9e5c2ae3aec`; each replay cell-metrics CSV is likewise byte-identical, SHA256 `3b67e093ae64c8300d681a7844f0fbdc514b2f545168a8aa780b52eab651697d`. Hence Python/package changes across these three runs did **not** change their numerical result.
- Archived accepted current-route CSV SHA256 `313e5f0459bf9f7c85fe15b7c5a37635dc4e6eca70c6c661cd4d55517a238d6c`; accepted FSFFL rolling-cell metrics SHA256 `ed37858d1e1a474d4ccabc4a160a239d3461046e3e9448493a816f0360b00b7c`; accepted board summary SHA256 `50c46c0a9ae6f618e3665bcde8f7bdf21dc9b8c0bead00ca0b98735b38ebb546`.

### Identity, route, policy, cardinality, provenance — exact parity on inspected board

1. **5,360/5,360 composite row keys match exactly** with no duplicates: canonical player ID, position, evaluation season, year index, target season and policy ID. Same **335 distinct reference players**: QB 61, RB 89, WR 121, TE 64; same 2026 season, Y4–Y7, four policies (baseline, hard_router, soft_stack, blanket_75_25), 64 position×horizon×policy cells.
2. **Zero differences in any board categorical authority field**: scoring coordinate `connected_league_fantasy_points`, model version `y4-y7-frozen-policy-fsffl-direct-materialization-v1`, source `fsffl:frozen_cell_routing_fsffl_scoring_recalibration`, and all **64 evidence paths**. Frozen/current route rows and soft/hard weights come from the same SHA256-checked `CURRENT_RESEARCH_ROUTE.csv` and frozen policy JSON; no route reselection or policy change occurred.
3. **Exact board-summary JSON equality** (governed scoring transform, season, policies, horizon, historical target, source, and no-reselection flags). All **64 calibration-metric row keys and support counts** match exactly. `coverage80` is identical in every cell; see the single `coverage90` threshold crossing below.
4. Accepted materializer blob `2b31040b2c38215636981ac7ad0744aaf759acee`, current connected 335-board input blob `72a2254a50aa96b2636064730f4b7cfccc005c21`, connected scoring rules blob `5e71a8fdce4294a0f8f1c0cad7c08406a771bebb`, and route policy freeze blob `beded6dd776719c19c7323d4e8fa5e4d4d81b0c0` **match Git blobs between the original accepted workflow head and PR1 base main**. Original dev/route source programs are explicitly restored from immutable accepted commit `be2541a...` and verified against blob IDs `ebb472514ece122bbdbabfe60cca991e5941ae1b` and `f932f07c9cb29b3c07352d48a928d0b190562a29`. All four accepted ZIP SHA256 values were independently checked in the replay and retention archive.
5. **Terminal limitation:** replay stdout/summary reports 335 generated terminal subjects and unchanged terminal coordinate, but the failed replay diagnostic ZIP did **not** include its terminal CSV/gzip. Therefore **byte-for-byte terminal row-value parity was not directly tested** in this diagnostic; do not claim it. The original reference terminal CSV remains preserved and has 335 rows. This is not evidence that terminal values differ.

### Numerical residuals — quantified, not accepted at current strict tolerance

The original PR1 comparator uses `math.isclose(ref, replay, rel_tol=1e-10, abs_tol=1e-8)` and exact categorical/row-key equality. Actual final Python 3.11 replay **fails 10,227 scalar comparisons across 16,080 board numeric entries** (3 × 5,360):

| Output family | Strict failures | Max absolute drift | Mean absolute drift | Max relative drift |
|---|---:|---:|---:|---:|
| Central Y4–Y7 expectation | 3,411 | `0.000923184256` points | `0.000009834805` | `0.0115293%` |
| Absolute-error 80 band | 3,408 | `0.024428190006` points | `0.003176902193` | `0.0895541%` |
| Absolute-error 90 band | 3,408 | `0.044141858239` points | `0.005401292150` | `0.0801542%` |

- **All 16 baseline policy cells replay to floating-point roundoff**: maximum central drift `2.42e-11`; corresponding bands differ at roughly `1e-12` or less. The first meaningful deviations arise in nonbaseline candidate fitting/combination, not in source-player identity, Y1 scoring coordinate, reference-year mapping, or the frozen baseline methodology.
- Cell-level dependency classification using exact frozen candidate weights: **24 cells** involve shared/global ridge combinations; **19 cells** include a histogram-gradient-boosting candidate; **21 cells** are specialist-ridge-only. 24/24 global-combination cells and 16/19 histogram-candidate cells have changes above `1e-8`; just 1/21 specialist-only cells does (RB Y4 hard_router, max central drift `2.28e-7`). Overall **23/64 cells** are indistinguishable under `1e-8` across central + bands. This is a model-numerics **path correlation**, not conclusive attribution to a specific BLAS operation.
- The 64-cell calibration diagnostics differ numerically in some `rmse` (max `0.006826`), `mae` (`0.006896`), `bias` (`0.011600`), `tail_rmse` (`0.013634`) and Spearman (`0.000213`). The same metrics' support counts remain exact; every `coverage80` matches. **One discrete threshold effect must not be hidden:** QB/Y4/`soft_stack` rolling `coverage90` changes from `0.903134` to `0.905983` — **one additional covered historical observation out of 351**. This does not imply rerouting because route/policy weights are frozen, but it refutes a claim of bit-identical calibration decisions.
- For diagnostic comparison only (not a Value/Decision acceptance test), **none of the 64 player orderings changes**, and none changes its top-ten player set. The maximum central difference is WR/Y5/`soft_stack` `0.000923184256` points. Future Career/Shapley sensitivity remains untested; do not claim that all downstream economic outputs would be identical.

### Source-vs-backend classification

- **No substantive input, accepted-source code, scoring transform, route, policy, subject identity, cardinality, or provenance discrepancy was found** in the artifacts/commands/blob hashes inspected. `route.fit_candidate` uses the same historical `target_season < T` training cutoff, frozen features and fixed evaluation cohort. Neither the 25 missing nor waiver players participate in fitting.
- The original accepted run and final replay both used **Python 3.11**, NumPy `2.4.6`, SciPy `1.17.1`, pandas `3.0.6`, scikit-learn `1.9.1`, cp311 wheels, GitHub-hosted Ubuntu 24.04.5 image `20260927.320.1`, and the same workflow materialization command/accepted code. Original runner region was **centralus**; final replay runner region **northcentralus**. Original/replay CPU microarchitecture, BLAS/OpenMP library runtime configuration, thread counts and floating reduction order were **not** captured.
- Replays from *three* differently prepared Python/library environments returned **byte-identical outputs**, but differ slightly from the October 3 frozen reference, with baseline ridge nearly exact and differences concentrated in complex/shared fits and downstream empirical residual quantiles. **Most consistent with host/backend-sensitive low-level numerical optimization or reduction behavior**, not new model logic. **Causal backend attribution is not proven** without captured/controlled CPU + threadpool/BLAS information from the original run, or an independently governed reproducibility envelope; identical versions alone cannot settle that. The accepted reference might encode a different allowed numerical execution trace, but there is currently no source evidence of a different methodological trace.
- Classification: **no demonstrated substantive input/methodology discrepancy; bounded numerical drift of presently unresolved backend cause, plus the one quantified calibration-threshold crossing.** This is *not* a green parity gate.

### Proposed principled parity criterion — MANAGEMENT APPROVAL REQUIRED, NOT ADOPTED

Separate acceptance into: **(A) bit/exact identity, cohort/route/policy/scoring-coordinate/source-blob/hash/schema invariants** (nonnegotiable); **(B) empirical numerical-backend reproducibility** (measure the clean-room dispersion of each output family under the same immutable historical inputs and accepted CPU/BLAS/OpenMP configurations, with no model-family or feature changes); **(C) materiality/semantic invariants** (forecast/value rank and absolute/relative impact measured against independently governed forecast uncertainty/calibration resolution, including threshold-crossing frequency, affected authority-map policy outputs, and downstream Career/Shapley sensitivity). Pre-register the comparison statistic, independent evaluation samples and pass/fail thresholds *before* using a new replay outcome. Do **not** choose `0.05`, `0.001`, decimal-place rounding, or another limit merely because this particular replay sits inside it. A calibration coverage threshold crossing must be reported and evaluated as a separate discrete diagnostic, not disguised by continuous tolerance. Explicitly capture runtime CPU, NumPy/SciPy/scikit-learn config, threadpoolctl/BLAS/OpenMP details for any **authorized** targeted reproducibility experiment.

Management must approve a numerically principled replacement for the currently strict deterministic test **only if** backend-only drift is sufficiently evidenced and the method/decision authority remains unchanged. A substantive new input/feature/model/route difference would instead require a distinct authority decision, not a tolerance exception.

**Next permitted action:** Management reviews this complete PR1 diagnostic and determines whether to authorize a narrowly specified numerical reproducibility criterion/instrumentation or stop PR1. Keep #429 draft, #405 active but blocked at the parity gate, and PR2–PR5 on hold. No new fit, rerun or model work is authorized by this diagnosis.

## PR1 semantic parity closeout — 2026-10-08 UTC / 2026-10-07 ET

**Disposition: PR1 SEMANTIC EVIDENCE COMPLETE — RETURNED FOR MANAGEMENT ACCEPTANCE; NOT SELF-ACCEPTED.** The newer Management instruction authorized this bounded downstream examination and supersedes the preceding checkpoint's pending review state. The existing fail-closed numerical board comparator (absolute 1e-8, relative 1e-10) **remains red, 10,227 / 16,080 numeric comparisons**. No chosen tolerance, new fit, training, route/model reselection, live-State mutation, deployment, merge, or PR2 development.

### Exact execution and permanently retained evidence

- Successful [semantic run 37721674872](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37721674872), code commit e01cb5103be11b5ef4cc26d101cc72f31e970f44, artifact [11526021872](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37721674872/artifacts/11526021872). Dedicated evidence-only script: scripts/verify_career_coverage_pr1_semantic.py. Initial harness runs 37721385586 and 37721449919 failed solely on CSV year_index string parsing and a mismatch between the **two original frozen ID formats** in the Current diagnostic. Corrected in harness with the exact 335-row source crosswalk (current_player_id → canonical player_id) from RECONCILED_PRESEASON_SOURCE_335.csv. No name matching or production changes.
- Successful separate **archive-only** [run 37721860189](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/37721860189), source commit 7a6a0ded89d6dd7cb3684c497e15658c9583467d, transferred the completed semantic evidence ZIP (career-405-pr1-semantic-11526021872.zip, SHA256 1bad20d2f4bc369d64f59f5ab2d2bd75117f594d45aeace352b58d4aedb3b2f3), plus SEMANTIC_SHA256SUMS, to the existing [durable evidence release](https://github.com/jderhagopian-stack/fsffl-next/releases/tag/career-405-accepted-research-evidence-20261007). All 11 release assets verified; archive job did **not** refit, rerun historical pipelines or execute Shapley. Frozen accepted board SHA256 f04547d3fae97420a12c13ff2f15010c9c54ec5b3a6af5ccd68927774aa12484; deterministic replay board SHA256 fd66a62f2c9fd71c6be00b980279af53446e980bba435a3bb07fd9e5c2ae3aec.
- **Terminal provenance gap CLOSED directly:** all 335 terminal feature rows recomputed from accepted immutable connected source board and historical season panel using unchanged FSFFL scoring feature logic, without fitting. Regenerated CSV is **byte-for-byte identical** to reference; both SHA256 ac7755962be04a51391120a8c92df31a1dfdca19368d3e6c0b3078745a7f9292; 0 numerical, categorical, key or provenance differences. Includes age, experience, current/prior points, missing-prior and exact scoring coordinates.
- Immutable release ZIP provides full row-level audit: terminal_parity.json; FOUNDATION4_CURRENT_TERMINAL_FEATURES_REGENERATED_335.csv; unchanged_current/SHAPLEY_CURRENT_BOARD_335.csv; career_335_player_differences.csv (335 players, every raw/low/high/width/rank/value delta); longterm_335_player_differences.csv (335 players, annual policy authority and 80/90 horizons); shapley_policy_contributions_differences.csv (3,242 supported policy-player-year observations and five scenarios each); dynasty_48_room_differences_SYNTHETIC.csv (every room raw, strength and rank delta); semantic_parity_summary.json; time.txt.

### Unchanged Career / Shapley / #370 counterfactual

Both accepted 5,360-row board and previously captured deterministic replay board were passed through **unchanged** Long-Term Intrinsic production function with governed 2,048 Monte Carlo Shapley permutations, horizon seeds 20260919, 20260920, 20260921, 20260922, 12-team FSFFL lineup 1QB/2RB/3WR/1TE/FLEX/SUPERFLEX, unchanged supported-policy map, and exact original set-valued authority envelope. Original Career tail function consumed exactly the same accepted 335 terminal features in each scenario. Original Career composer consumed same unchanged 335-player Y1–Y3 Current Shapley frozen diagnostic, exactly canonical-ID mapped, for both scenarios. This is a **frozen-cohort sensitivity test**, not a reconstruction of the current live league's dynamically updated Y1–Y3.

**Numeric Career economics (all 335):** all 335 continuous raw Career outputs differ, but **0/335 Career ranks change**. Max/mean absolute raw Career delta 0.0003628406101370274 / 0.00002339184658647933 FSFFL fantasy-point units. Y4–Y7 raw contributes all change; **Y1–Y3 and terminal Y8+ differences are zero**. Career model-authority low max/mean 0.00037247911416216084 / 0.00002670424998875005; high max/mean 0.0003532021062255808 / 0.000020172653674617977; width max/mean 0.00021494539259947487 / 0.00001143854762524177. Full per-player fields retained.

**Long-Term economic scale:** **0/335 rankings** and **0/335 0–10,000 rank-calibrated display indexes** change. The *minimum* frozen Career adjacent-rank gap is 0.004276660043089464; worst possible two-sided movement bounded by **2 × max observed individual raw delta = 0.0007256812202740548**, strictly below the closest gap. This is an independent, mathematically checkable **ranking stability certificate for this cohort and unchanged Current**, not a universal numerical tolerance.

**Shapley uncertainty / annual policies:** 3,242 governed policy-player-year comparisons, five scenarios each. Max abs central Shapley delta 0.00021633802175813344 (3,233 nonzero); lo80 max 0.024544433452604153 (844 nonzero); hi80 max 0.02448349119842419 (3,232 nonzero); lo90 max 0.04404014592582861 (322 nonzero); hi90 max 0.04424357054926986 (3,214 nonzero). All annual raw/authority and outer-band deltas retained in the CSVs. Do not conflate these real uncertainty-band differences with exact numeric replay.

**#370 actual function sensitivity:** existing build_dynasty_position_rooms ran unchanged for both Career contracts on a **synthetic, complete, 12-team × 18-player League State, comprising 216 accepted-cohort players**; all 48 rooms were evidence-complete; **0/48 team-position league ranks changed**, largest room raw-total delta 0.0006206368880157243, largest strength-index delta 0.000010985159974552516. This fixture is deliberately **NOT the actual league State**. Actual live #370 rank/readiness invariance CANNOT be asserted: the 25 previously missing rostered players still block a complete live Career universe, for PR2 onward after PR1 acceptance.

**Discrete calibration caveat still open:** The preexisting rolling QB Y4 soft-stack historical 90% coverage difference is **one of 351 observations**, although frozen policy/authority sets and tested Career/rank outcomes remain invariant. Do not conceal this discrete diagnostic by rounding or continuous-error averaging. Backend CPU/BLAS variation remains a plausible but **unproven cause**, not the finding.

### Proposed principled reproducibility gate — Management decision, NOT automatically adopted

**Tier A (exact, nonnegotiable):** unchanged accepted research Git/source/route/policy/scoring/training inputs, source SHA hashes, 335 identities / 5,360 row keys / 64 cells, original model & scoring/evidence contracts, supported-policy sets and weights, complete byte-identical terminal 335. Any methodological/source/route difference is an automatic failure, not numerically tolerable.

**Tier B (decision-semantic, explicit):** use the unchanged original 2,048-permutation Shapley, Current/Y8+ evidence held identical; assert no changed supported policy, authority kind, readiness/coverage outcome, governed Career or Long-Term ordering, rank-calibrated 0–10,000 indexes, or same-State #370 team-room ranks for whichever cohorts have full coverage. Require machine-readable numerical deltas **for every** raw Career center/low/high/width and every annual 80/90 uncertainty boundary, and certify ranks by each measured reference adjacent margin versus **worst-case pairwise movement**, *not an arbitrary points threshold chosen from this result*. Treat original 1/351 coverage90 threshold crossing separately as discrete diagnostic governance. Test the actual same-State production #370 only **when coverage is complete**; synthetic result alone is not live evidence.

**Tier C (numeric reproducibility, Management-approved only):** leave strict 1e-8/1e-10 comparator red and visible. Any future numerical backend envelope or published reporting precision must be independently justified/pre-registered, not tailored to this observed maximum, and CPU/BLAS causality must not be asserted from current data. Management can explicitly accept PR1's unchanged authority and outcome **semantic reproducibility with the documented residual numeric failure**, or require additional narrow evidence. Do not silently replace acceptance with an arbitrary 0.05/0.001 tolerance or rounding rule.

**Management acceptance — 2026-10-07 ET:** **PR1 ACCEPTED.** Management adopts the proposed three-tier reproducibility rule for this pipeline: Tier A exact authority/provenance/identity/route/policy/scoring/terminal invariants are nonnegotiable; Tier B requires explicit downstream semantic stability under the unchanged governed Career/Shapley/#370 path for fully covered cohorts; Tier C keeps raw numerical drift measured and visible and does not replace the historical strict comparator with an outcome-tailored epsilon. The existing `1e-8 / 1e-10` frozen-board comparator therefore remains red as historical numerical evidence, but it is no longer by itself a blocker when Tier A is exact and Tier B proves unchanged governed conclusions. The one-of-351 QB/Y4 soft-stack coverage90 threshold crossing remains a separately disclosed diagnostic and is not rounded away. This acceptance is specific to the preserved #405 PR1 evidence; it does not grant a generic tolerance for future model changes.

PR1 may now advance through the repository's normal exact-head stable full-suite gate and merge if green. No Render deployment is required for PR1 because this tranche changes evidence-preservation/replay tooling and operations documentation, not hosted production semantics. **PR2 becomes authorized only after PR1 is merged and checkpointed on main.** PR2 must follow the existing dynamic-evidence, season-rollover, multi-league reuse, bounded-resource and no-retuning contracts already recorded above.
