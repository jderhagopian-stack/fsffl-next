# FSFFL NEXT — Forecast / Product Implementation

Updated: 2026-09-25

## State
**DIRECTIVE COMPLETE — HODOR SHARED-FORECAST POPULATION + PARTIAL-COVERAGE CORRECTIVE**

Management has superseded the prior blanket “external evidence blocks further implementation” stop for the current Hodor population issue. Full K/DST authority remains externally gated, but that gate may not collapse otherwise valid canonical Forecast coverage.

The governing decisions are now:
- one canonical league-agnostic player/stat Forecast truth; league scoring is a downstream transformation;
- valid governed forecastable coordinates remain usable even when some active scoring events are unsupported or inherently unforecastable;
- missing evidence must never silently become zero;
- bounded rare/special-event gaps may produce explicit PARTIAL / PROVISIONAL scored outputs with omitted-coordinate metadata and downstream authority limits;
- only a materially disqualifying missing coordinate may block the affected subject/consumer, not unrelated positions or the entire league;
- the Hodor Performance lifecycle corrective is complete at PR #242; Forecast/Product now owns the remaining Hodor population blocker.

### Current Hodor production evidence
The historical Hodor failure was `LiveForecastSourceHealthFailure: authoritative live ensemble found 0 qualifying independent full-season sources under Hodor scoring`. That league-wide Forecast failure is resolved.

PR #244 merged at `edb9c0f9a1ccea4250761c63f65694d449c2d285`. An authenticated production Hodor refresh then advanced through shared Forecast population rather than failing `BUILDING_FORECASTS`: 330 player-scoring outputs were explicitly partial, and Simulation was withheld with `partial_player_scoring_coordinates_present` plus `separate_k_dst_forecast_authority_required`. Current Value became available.

PR #245 merged at `7ad0d5ce4be038a2615433467227cdcfd3da85a4` after 1,620 full-suite tests and all configured focused workflows passed. Render deploy `dep-daredcl9fdbs7398s55g` is live on that exact merge. Its startup restored Hodor league `sleeper:1397623301961981952`, refreshed State `d28de4cca9d35faeb88446449ef09984cdb57c753ef835121d70101ca56b31cb`, with `forecast=True simulation=False value=True complete=False`. The partial-authority state therefore survives restart without promoting blocked Simulation.

Durable closeout:
- `artifacts/implementation/hodor_shared_forecast_20260925/IMPLEMENTATION_HANDOFF.md`

### Authorized corrective
Forecast Implementation must:
1. trace why league-specific Hodor scoring is rejecting or hiding otherwise valid shared canonical QB/RB/WR/TE statistical Forecast evidence;
2. restore the approved boundary: canonical football-stat Forecast is league-agnostic, and Hodor scoring is applied downstream without creating a duplicate league-specific projection database;
3. implement FULL / PARTIAL-PROVISIONAL / UNSUPPORTED behavior so supported coordinates populate even when bounded scoring components cannot credibly be forecasted;
4. ensure unsupported events are explicit omissions with reason/coverage metadata, never fabricated and never silently zeroed;
5. isolate materiality at the affected subject/consumer boundary rather than treating one unsupported coordinate as a total-league Forecast failure;
6. reconcile PR #238 onto current main and preserve exact league/state binding for provisional K/DST scored outputs;
7. trace the 2026 provisional K/DST path end-to-end and explain/repair why production currently has zero provisional artifacts wherever governed supported evidence is actually available;
8. keep genuinely unavailable K/DST components explicit while allowing independently valid offensive Forecasts and other supported projections to populate;
9. carry the corrective through tests, merge, Render deployment, and production Hodor validation before returning control.

Full K/DST authority still requires its existing external source/rights/exact-coordinate/uncertainty gates. This directive does not authorize fabricated 60+ FG frequency, nonlinear PA-bucket reconstruction from aggregate means, invented rare-event rates, invented source rights, or silent promotion of partial evidence into full Value/Simulation/Decision/Search authority.



### Generic Sleeper-league acceptance requirement
This corrective is architectural, not Hodor-specific. Production behavior must contain no special casing for Hodor, `jder52`, any known Sleeper league ID, or any known franchise ID.

Acceptance must prove that the same pipeline works when supplied an arbitrary valid Sleeper league identity/state:
- connect/select the league through the normal Sleeper path;
- preserve the league's actual scoring/rules/state identity;
- reuse canonical league-agnostic player/stat Forecast evidence;
- derive league-specific scored outputs from those rules;
- isolate K/DST or other unsupported subject/rule families without erasing unrelated valid Forecast;
- emit FULL / PARTIAL_PROVISIONAL / UNSUPPORTED / NOT_APPLICABLE from capability/evidence, not league-name or league-ID branches.

Hodor may remain a regression fixture because it exposed the defect, but Hodor-specific fixture names or expected outputs are not sufficient acceptance. Add deterministic coverage using arbitrary/synthetic league IDs and materially different scoring profiles. Existing Sleeper cross-league selection tests must remain green.

The intended product contract is: a user may enter/select any valid Sleeper league ID; FSFFL NEXT loads its State/roster and computes every intelligence layer that the league's rules and governed evidence support. Unsupported or unforecastable coordinates degrade only the affected capability and are reported explicitly rather than causing league-wide failure.

### Acceptance target
Production acceptance requires the correct Hodor league/state and roster plus supported canonical Forecasts populated from shared player/stat evidence, truthful FULL/PARTIAL/UNSUPPORTED coverage by affected subject/rule family, explicit omitted-coordinate reasons, and a precise residual blocker for any downstream capability that still cannot operate.

Do not reopen generic source Research merely because a bounded scoring event lacks a credible projection. Some scoring events may remain explicitly unforecastable; that is a coverage condition, not automatically a total Forecast failure.

Management accepted the completed K/DST + late-connect Research contract and authorized its bounded implementation. The base architecture remains authoritative:
- `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`

Management's current implementation authority is:
- `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`
- `artifacts/implementation/k_dst_late_start_20260925/IMPLEMENTATION_HANDOFF.md`

Implementation PR **#215** is merged on canonical main at `407c1bf85e5dc75f92b9906719f82bcd11d97c31`.

Management-authorized late-start implementation PR **#233** is merged on canonical main at `79c1f0c0aa094e4b1e3f6aa41eacd08c6bf1d6e8`. Its reconciled head `1e9eb293c7029b0953c3ecec8353b8c2638ea35e` passed full CI, PR164 focused corrective regression, Live Forecast corrective trace, and Corrective live provider numerical trace before merge.

## Implemented in the active PR
### Stage 1 — contracts and scoring
- canonical NFL team identity/aliases shared across State and Forecast;
- K remains an individual-player Forecast family;
- D/ST has a canonical NFL team-season Forecast subject and player-shaped D/ST observations are rejected;
- K and D/ST raw metric contracts are explicit;
- rule-level source evidence carries an independence-group identity;
- K exact vs exact-derived coverage is explicit, including no 50+ heuristic split into 50–59 / 60+;
- D/ST linear event scoring is distinct from per-game distributional points/yards-allowed bucket scoring;
- team special-teams and player special-teams semantics remain separate;
- active missing `fum_lost` evidence fails closed rather than silently contributing zero;
- CBS no longer manufactures a zero fumble-loss projection when the provider column is absent;
- Sleeper rostered D/ST assets retain canonical team identity for the roster→Forecast team-unit boundary;
- unrostered Sleeper player enrichment includes K but does not reinterpret D/ST as a player Forecast subject.

### Stage 2 — non-promoting research harness
- deterministic nflverse-style K realized-outcome reconstruction;
- conservative directly observable D/ST realized-event reconstruction;
- explicit missing kick-distance completeness defects rather than guessed distance bands;
- non-promoting season-error fitting gated on at least two independent sources;
- weekly volatility fitting uses realized game scores rather than season-total / 17 shortcuts.

## Authority deliberately not promoted
The PR does **not** create or claim:
- live K/D/ST provider authority;
- a K or D/ST production uncertainty coefficient;
- a qualifying 2026 K/DST preseason baseline;
- current/post-opener data relabeled as preseason;
- annual-snapshot-v2 migration acceptance;
- K/DST Value, Simulation, Decision, Search, or Presentation truth;
- any weakening of the existing two-independent-source requirement.

## Acceptance validation
The first PR run correctly exposed historical synthetic fixtures that had relied on an implicit missing-`fum_lost` zero. Those fixtures were repaired by supplying explicit synthetic zero observations only where the fixture itself owns that evidence. Runtime/provider evidence remains fail-closed.

After reconciliation with concurrent Market operating-state changes, the final PR #215 head passed full CI, focused corrective regression, private-beta Intrinsic diagnostics, live Forecast corrective trace, and the governed live-provider quarantine trace, then merged to main.

Post-merge Stage 2 evidence recovery was also attempted. The result is persisted in `artifacts/implementation/forecast_k_dst_contracts_20260924/EVIDENCE_GATE_CHECK_20260925.md`: no qualifying second historical independent K/DST PIT corpus was recovered, and candidate production sources remain rights/licensing gated.

## Remaining evidence gates after PR #233
The bounded implementation is complete. Production K/DST authority remains fail-closed until:
1. authorized live API/source access and deployable rights are available for an exact-capability provider path;
2. a second independent current ROS source proves the Hodor-specific K 60+ coordinate;
3. a second independent current ROS source proves D/ST remaining-game PA distribution plus the remaining rare-event coordinates;
4. target-compatible full-score K and D/ST uncertainty is empirically promoted under an exact scoring fingerprint;
5. only after Forecast authority is genuinely green, the new-league lifecycle is re-run for downstream acceptance.

The 2026 preseason comparison remains explicitly unavailable where authentic pre-Week-1 K/DST evidence does not exist. Missing preseason evidence is no longer a current-forward blocker.

These are external evidence/rights dependencies. They may not be bypassed with offense coefficients, one-source estimates, synthetic production values, zero uncertainty, average-based D/ST bucket reconstruction, or backdated current data.

## 2026 late-start exception implementation
Management superseded the prior blanket implementation stop with a bounded one-season-only 2026 current-date ROS authorization. PR #233 completed that evidence-independent implementation while preserving the remaining rights/exact-coordinate/uncertainty gates.

The merged implementation includes the dedicated non-preseason artifact, hard 2026 boundary, schedule-aware row quarantine, rights-aware independent-source coverage, K/DST ROS normalization, exact K algebraic transforms, explicit calibration fingerprints, deterministic replay/holdout diagnostics, and no-zero-uncertainty authority assessment.

The late-start artifact is not preseason authority. It is hard-disabled for 2027+.

## Corrective terminal state
The Hodor/shared-Forecast corrective is accepted and complete. Canonical raw player/stat Forecast is league-agnostic; scoring-family gaps now degrade only affected scored outputs/consumers; partial omissions are explicit; Simulation is gated separately; and the same behavior is regression-proven across unrelated synthetic Sleeper league identities and scoring profiles.

No further implementation is authorized merely to make Hodor fully scored. Full K/DST authority remains a distinct external-evidence dependency. Resume that authority program only when authorized API/source access or a newly supplied independent exact-capability source can materially clear a remaining gate. Do not substitute heuristics.

**DIRECTIVE COMPLETE — FORECAST / PRODUCT IMPLEMENTATION — HODOR SHARED-FORECAST / PARTIAL-COVERAGE CORRECTIVE**

Residual full K/DST authority: **BLOCKED — EXTERNAL SOURCE RIGHTS + SECOND-SOURCE EXACT COORDINATES + TARGET-COMPATIBLE UNCERTAINTY**


## Physical iPhone acceptance — Hodor partial-Forecast pass
**State: ACCEPTANCE FAILED — READINESS/PRESENTATION SEMANTICS CORRECTIVE REQUIRED**

Management physical-iPhone/Safari evidence after the Hodor shared-Forecast corrective shows materially improved lifecycle population but an internally inconsistent product state.

Observed:
- prior state showed Hodor / jder52 at 2/7 with an empty roster;
- current state shows Hodor / jder52 at 7/7 with “Core intelligence current” and a valid 16-player roster;
- Home simultaneously shows Position pressure point unavailable and Current Simulation unavailable;
- Franchise shows “Forecast / Simulation-derived fields are unavailable,” no position-strength evidence, and Not Classified;
- League Atlas standings/position-strength cells remain unavailable while the surface text still references 50,000 simulations using current standings, rosters and forecast evidence;
- Value Map shows Broad Market values for players where available but FSFFL Intrinsic remains unavailable;
- future-pick rows show Broad Market value unavailable.

Management acceptance interpretation:
1. The architectural correction is directionally successful: valid State/roster now survive and shared Forecast can populate without K/DST collapsing the entire league.
2. The green 7/7 “Core intelligence current” presentation is not acceptable when governed Simulation/position-strength/classification/Intrinsic outputs that the UI presents as core intelligence are unavailable.
3. Job/lifecycle completion must be distinguished from intelligence-capability readiness. “Completed” may truthfully mean the pipeline exhausted all authorized work and reached a stable partial-authority state; it must not automatically render as “7/7 Core intelligence current.”
4. The readiness UI must expose capability state, not just stage completion. Full vs partial/provisional vs unavailable must be explicit for Forecast, Simulation, Value/Intrinsic, and derived surfaces.
5. Surfaces must not display descriptive copy that implies unavailable analytics are present (for example “50,000 simulations using current standings, rosters and forecast evidence”) when Simulation is authority-blocked.
6. A valid arbitrary Sleeper league may legitimately reach a stable partial-authority state; that state is acceptable only if the UI accurately represents what is and is not available.
7. Hodor-specific behavior remains prohibited. The corrective must apply generically to any valid Sleeper league/state.

Required corrective:
- separate lifecycle/job completion from intelligence readiness;
- redefine the top readiness indicator so green/full status is earned only by the capabilities that the label claims are current;
- if retaining a 7-stage lifecycle counter, label it as lifecycle/build completion and separately show capability readiness;
- ensure Home/Franchise/League/Market copy and badges consume the same governed capability truth;
- preserve the existing partial-Forecast architecture and do not weaken K/DST/Simulation/Value authority merely to make the badge green;
- validate on Hodor plus arbitrary/synthetic Sleeper league IDs and at least one fully supported existing league;
- continue through tests, merge, Render deployment, and production physical-device-ready validation before returning control.

This is a product truth/acceptance issue, not permission to fabricate missing Simulation, Intrinsic, position-strength, or K/DST authority.


## Root-cause diagnosis — Hodor post-PR245 physical pass
Management traced the post-PR245 Hodor partial-authority state against production code and persisted Hodor State.

### 1. Ordinary player Forecasts are partial because active `fum_lost` scoring lacks raw Forecast evidence
The persisted Hodor scoring contract includes `fum_lost = -2` in addition to ordinary pass/rush/receive scoring. The current league-scoring bridge explicitly treats active FUMBLES_LOST as a standalone material coordinate: if it is scored and absent from a player's raw Forecast evidence, that player's fantasy-point total is emitted only as PARTIAL_PROVISIONAL rather than authoritative.

PR #245 production evidence reported `partial_players=330` and blocker `partial_player_scoring_coordinates_present`. Given Hodor's active ordinary-player rule set and the current bridge contract, missing FUMBLES_LOST evidence is the material ordinary-player coordinate causing this league-wide partial-player condition. Do not solve this by silently assigning zero fumbles lost.

This is a Forecast evidence/model gap that should be corrected generically if governed FUMBLES_LOST projection evidence can be produced. It is distinct from rare-event omissions such as 60+ FG increments.

### 2. K/DST independently blocks full Simulation authority
Hodor starts both K and D/ST and its active rules include K distance bands through 60+, FG misses, D/ST PA buckets, blocked kicks, defensive two-point returns and team special-teams events. Current family coverage therefore also emits `separate_k_dst_forecast_authority_required`.

This does not erase shared offensive Forecast anymore, but current Simulation admission requires `uncertainty_ready`, which is false whenever Forecast reports any Simulation authority blocker. Therefore no current 50,000-run Simulation is promoted.

### 3. Position strength, competitive classification and season outlook are downstream of Simulation
The live Simulation runtime is where optimized lineups, league-relative position strength, expected wins/playoff/championship distributions, Team Utility and calculated competitive state are assembled. When Simulation is not promoted, these fields remain unavailable by design. Their blank presentation is downstream consequence, not separate source failure.

### 4. FSFFL Intrinsic is a separate late-connect preseason-bootstrap gap
Broad Market Value is current-market evidence and can load independently. Canonical Shapley Intrinsic currently uses the preserved preseason Year-1 authority loader and requires `evidence_basis=preseason_baseline`. That loader is still scoped to the league-season artifact. A league connected after preseason therefore has no league-scoped preserved Year-1 baseline even when authentic league-agnostic pre-kickoff raw offense evidence exists elsewhere.

This is inconsistent with the already-approved late-connect architecture: authentic preserved league-agnostic PIT raw-stat evidence should be reusable/re-scored for a newly connected league without backdating current evidence. Forecast/Product should repair that bootstrap path for supported player families. Missing authentic K/DST preseason evidence remains unavailable rather than fabricated.

### 5. Draft-pick Broad Market blanks are a separate wiring issue
The current market runtime can produce pick cardinal / pick-variant evidence separately from player MarketPriceEstimate rows, while the Franchise pick presentation attaches `value_profile` only from the player-style `estimates` mapping. Therefore visible pick rows can show Broad Market unavailable even when pick evidence exists elsewhere. This is Presentation/Value wiring, not evidence that all pick market data is absent.

### 6. Green 7/7 is a readiness-semantics bug
PR #245 truthfully permits a background intelligence job to complete in a stable partial-authority state. However the top shell still maps that completed lifecycle to green `7/7 Core intelligence current`. Lifecycle completion must remain distinct from capability readiness.

Required corrective scope should therefore target these separate causes rather than treating all blanks as one failure.


### Non-regression guardrails for the post-PR245 corrective
The post-PR245 corrective must be backward-compatible with previously accepted behavior except where Management explicitly authorizes a truthfulness correction.

Required protections:
- existing fully supported leagues must retain their current State/Forecast/Simulation/Value capability unless a newly corrected governed Forecast input legitimately changes a model output;
- existing league-scoped preserved preseason baselines remain authoritative and must not be replaced by the late-connect bootstrap path; late-connect reuse is fallback/bootstrap only when the league-season artifact does not already exist;
- shared canonical raw Forecast evidence remains one authority; no league-specific duplicate projection database or Hodor special case may be introduced;
- adding governed FUMBLES_LOST evidence may legitimately change fantasy-point projections for leagues that score fumbles lost, but the change must be traceable to that newly supported coordinate and must not alter leagues whose scoring does not consume it;
- full K/DST authority gates, source-rights gates, uncertainty gates, and exact-state binding remain unchanged;
- accepted Market discovery, Decision-screen, zero-broad-changed-state-Simulation, Value authority separation, and existing lifecycle last-good restoration semantics must not change;
- the readiness correction may change labels/status presentation where the prior UI overstated capability; this is an intentional truthfulness correction, not permission to regress actual available intelligence;
- regression validation must include Hodor, arbitrary/synthetic Sleeper leagues with different scoring, and at least one existing fully supported league with previously complete intelligence. Existing full-capability outputs should remain within expected deterministic/model-version deltas and any intentional numerical change must be explained by the corrected Forecast coordinate.


## Physical iPhone acceptance — existing FSFFL league regressed after league switch
**State: ACCEPTANCE FAILED — EXISTING FULLY SUPPORTED LEAGUE / SWITCH-RESTORATION NON-REGRESSION**

Management physically switched from Hodor back to the existing fully supported FSFFL Dynasty league (`sleeper:1312071960615731200`, managed team `jimmygoodjob`) on iPhone/Safari.

Observed UI:
- shell reports green `7/7 Core intelligence current`;
- Home simultaneously shows `Position pressure point unavailable`;
- Current Simulation is unavailable;
- expected wins / playoff / championship are blank;
- franchise classification is `Not Classified`;
- position-strength rows are blank.

Durable database evidence:
- prior accepted fully supported State `203227df88b78cdd1c0a0861bc16cae0157abd91b52a3ef9ee1278f129a462ed` still has non-invalidated `current_forecast_evidence`, `live_simulation_analytics`, and `current_market_value` artifacts;
- current selected FSFFL runtime context moved to State `8cd7b3cb80c924304e8a1bc33eecce020236efd175b33ef138ac66e97fe0c5ab`;
- the old complete intelligence bundle was therefore not deleted or corrupted;
- the new State is not byte-identical to the old State: league/teams/draft-pick ownership remain equal, while time-sensitive fields such as matchups, player/player-state, team-state, NFL byes, provenance and as-of changed.

Acceptance interpretation:
1. This is not evidence loss. The accepted complete FSFFL bundle still exists.
2. Because the newly selected canonical State materially differs, exact-state binding correctly prevents blindly attaching the old Simulation/Value bundle as current truth.
3. The product still fails the switching/lifecycle contract because a switch to an existing league may not present `7/7 Core intelligence current` while serving a new exact State with no current Simulation/position-strength/classification.
4. League switch must immediately distinguish:
   - usable canonical current State;
   - compatible reusable Forecast evidence;
   - last-good but stale exact-state intelligence;
   - current enrichment status / exact blocker.
5. If the current State requires recomputation, the shell must show that work truthfully and preserve safe last-good context only as explicitly stale/non-current evidence. It must not present lifecycle completion from the previous state/league as current 7/7.
6. Regression acceptance now requires switching Hodor → FSFFL → Hodor (and arbitrary valid Sleeper identities) without cross-state/cross-league readiness leakage, while preserving exact-state authority.

Do not use this incident to weaken exact-state binding or silently reuse stale Simulation. Repair switch/restoration/readiness orchestration and continue the already-authorized post-PR245 corrective through tests, merge, Render deployment, production Hodor validation, and production existing-FSFFL switch/regression validation before physical Market acceptance resumes.


### League-switch recomputation requirement
Management clarifies that last-good/exact-state restoration is an optimization and resilience mechanism, not a prerequisite for correctness.

When a user selects or reconnects any valid Sleeper league:
1. load and expose the current canonical LeagueState immediately;
2. attempt to reuse only intelligence artifacts that are provably compatible with that exact State / Forecast coordinate under existing authority rules;
3. if no compatible current bundle exists, automatically start or resume the normal governed enrichment pipeline for that newly selected State;
4. surface persistent progress/status while enrichment runs;
5. promote Forecast / Simulation / Value / derived analytics atomically when each authority gate clears;
6. if a stage cannot clear, expose the exact capability blocker while preserving usable State and any independently valid upstream evidence.

A previously complete league must therefore be able to reproduce its intelligence from canonical State + governed Forecast/Value inputs even if its prior complete bundle cannot be reattached. The product may not depend on finding a historical last-good artifact in order to become useful again.

Acceptance must prove both paths:
- **reuse path:** compatible persisted intelligence is restored without recomputation;
- **rebuild path:** when compatible intelligence is absent or stale, the app automatically recomputes the current State to the same governed capability level that the league's rules/evidence permit.

Do not weaken exact-state binding, source authority, or uncertainty gates to achieve this. The rebuild must use the same canonical Data → State → Forecast → Value → Simulation/Team Utility authority chain as a fresh valid league load.

For the current FSFFL regression, Management expects that the new State either:
- reuses compatible Forecast components and recomputes only invalidated downstream layers where allowed; or
- performs a full governed enrichment for the new State if compatibility cannot be proven.

In neither case may the shell claim green/full readiness before the current-State capabilities actually exist.


### Refresh Intelligence = league sync + intelligence reconciliation
Management defines the user-facing **Refresh Intelligence** action as the canonical manual league-sync/update operation, not merely a model rerun against the currently loaded State.

Required order of operations:
1. fetch/revalidate the currently selected Sleeper league from the provider;
2. persist/select the resulting canonical current LeagueState;
3. compare the new State to the prior State and determine which persisted intelligence remains provably compatible;
4. reuse compatible artifacts only under existing exact-state/input-fingerprint authority rules;
5. automatically rebuild every invalidated or missing governed layer for the new State;
6. expose persistent progress and exact capability/blocker status until reconciliation terminates;
7. atomically promote newly valid Forecast / Simulation / Value / derived analytics for the current State.

The current implementation path is not sufficient for this contract because `POST /api/intelligence/jobs` presently invokes the Forecast loader on the already-loaded `initial_state` before it refreshes canonical Sleeper State. A manual sync must not compute new intelligence from an old State and then attach/reconcile it onto a newly fetched State unless compatibility is explicitly proven.

Acceptance:
- a no-change sync should cheaply retain/reuse current governed intelligence;
- a changed-State sync should invalidate only affected layers and recompute them;
- a material roster/rules/matchup/player-state change must never leave stale downstream intelligence labeled current;
- if current evidence cannot rebuild a layer, the exact blocker must be surfaced while current canonical State remains usable;
- repeated manual Refresh Intelligence calls must be idempotent for an unchanged provider State;
- league switching and manual refresh must use the same underlying State-first reconciliation contract rather than separate semantics.

Product semantics:
**Refresh Intelligence = Sync league + refresh/reconcile intelligence.**
The existing button label may remain for now, but user-facing status should make the sync/rebuild lifecycle clear. A future wording change such as `Sync & Refresh` may be considered separately if physical testing shows the action remains ambiguous.

Do not weaken exact-state binding, Forecast authority, Value authority, Simulation gates, or last-good safety to satisfy this behavior.


## State-first corrective terminal handoff — 2026-09-26
**State: MANAGEMENT GATE — FUMBLES_LOST FORECAST AUTHORITY**

PR #246 and PR #249 complete the State-first league-sync, reuse-or-rebuild, and truthful capability-readiness contract. PR #251 makes preserved-preseason fallback replay retain truthful partial coverage; PR #252 invalidates stale pre-corrective Forecast artifacts so current State rebuilds under the new contract.

Production acceptance on current FSFFL State proves:
- canonical State current;
- current Broad Market/Value FULL;
- 1,675 raw Forecast observations;
- 335 partial player Forecasts;
- Forecast `partial_provisional`;
- Simulation unavailable;
- unique omitted active ordinary-player rule: `FUMBLES_LOST`.

The remaining failure is not league switching/rebuild/readiness orchestration. Under current authority, FUMBLES_LOST is core/material and the two-source preserved baseline contains no such coordinate. Implementation may not fabricate zero, borrow a different horizon, reuse stale full artifacts, or apply the auxiliary-single-source exception.

Durable handoff: `artifacts/implementation/state_first_fumbles_authority_20260926/IMPLEMENTATION_HANDOFF.md`.

Implementation waits for qualifying evidence or an explicit Management authority-policy decision. Market full physical acceptance remains paused because the current FSFFL state cannot promote Simulation.


## Management authorization — prepare 2026 ordinary-offense ROS lane
**State: AUTHORIZED PENDING QUALIFYING SOURCE EVIDENCE**

Management authorizes the product/Forecast architecture for a 2026 current-ROS ordinary-offense lane. Implementation may prepare provider-neutral horizon/artifact contracts, replay/fingerprint safety, current-forward consumer routing, provenance/coverage diagnostics, and tests that do not fabricate provider evidence.

Do not promote production ROS authority until Research supplies a qualifying same-horizon multi-source evidence package. Do not splice a ROS FUMBLES_LOST coordinate into the preserved preseason baseline.

When qualifying evidence arrives, implementation should:
- materialize one canonical current-ROS raw-stat Forecast ensemble for ordinary offensive players;
- preserve the authentic preseason baseline as a separate PIT artifact;
- score the ROS raw Forecast under each connected league's rules;
- rebuild current Forecast/Simulation/derived intelligence for the exact State;
- prove existing-league full capability and arbitrary-league non-regression;
- continue through CI, merge, Render and production validation before Management physical testing resumes.


## Management correction — implement only bounded FUMBLES_LOST supplementation
**State: AUTHORIZED PENDING QUALIFYING FUMBLES_LOST EVIDENCE**

The whole ordinary-offense ROS rebase is superseded.

Implementation should preserve the existing preseason/full-season ordinary-offense Forecast and add only a provider-neutral **current FUMBLES_LOST supplemental evidence contract** once Research supplies qualifying evidence.

The implementation must:
- keep the immutable preseason artifact unchanged;
- retain exact source acquisition/effective time and ROS/current horizon;
- normalize the supplemental coordinate to the scorer/Simulation's target period or rate explicitly;
- tag current scored Forecast lineage as supplemental/mixed-vintage where consumed;
- exclude the supplement from preseason/PIT historical comparisons;
- require two-source material-coordinate authority and target-compatible uncertainty;
- avoid changing leagues that do not score FUMBLES_LOST;
- rebuild only affected current Forecast/Simulation/derived artifacts;
- prove no unrelated ordinary-player raw-stat projection changes.

No current provider is promoted by this authorization.


## First-party FUMBLES_LOST integration directive — 2026-09-26
**State: ACTIVE — FIRST-PARTY MODEL INTEGRATION / PRODUCTION ACCEPTANCE**

Research is complete and merged through PR #256. The accepted first-party model is:
`next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate`.

Authoritative Research handoff:
- `artifacts/research/fumbles_lost_first_party_model_20260926/PRODUCTION_READINESS_HANDOFF.md`
- `artifacts/research/fumbles_lost_first_party_model_20260926/MODEL_SPEC.md`
- `artifacts/research/fumbles_lost_first_party_model_20260926/CURRENT_INPUT_ASSESSMENT.md`

Implementation must now complete the recovery path through production acceptance:
1. wire the frozen first-party model into the already-merged PR #253/#255 current-supplement seam;
2. use exact lost-fumble semantics and the accepted Week-2/current-state opportunity inputs only;
3. reproduce the frozen 2026 calibration scalar and non-zero uncertainty contract exactly;
4. preserve every unrelated offense Forecast coordinate and the immutable preseason/PIT baseline;
5. fail closed for missing/ambiguous identity or required current evidence; never substitute zero;
6. rebuild current FSFFL Forecast/Simulation/derived intelligence for the exact current State;
7. prove leagues not scoring `fum_lost` are regression-identical and Hodor/partial-authority behavior does not regress;
8. run focused tests + full CI, merge the implementation PR, deploy Render, and validate production FSFFL reaches legitimate full current player-scoring authority and Simulation before returning control;
9. persist exact production evidence and stop only at a permitted `OPERATING_PROTOCOL.md` terminal state.

Do not reopen provider-permission Research, broad scoring coverage, K/DST authority, Market redesign, or long-horizon Intrinsic work in this corrective.


## Post-PR #257 production-acceptance checkpoint — 2026-09-26
**State: ACTIVE — POST-MERGE CI CORRECTIVE + PRODUCTION REBUILD VALIDATION**

PR #257 (`f07252b1dd19307c3b3c8f769cabfee7de7d6fac`) is merged and live on Render as deploy `dep-darki1g473hc73bb7aeg`.

Pre-merge acceptance:
- PR CI: green;
- PR164 focused corrective regression: green;
- Live Forecast corrective trace: green;
- Corrective live provider numerical trace: green.

Post-merge main CI is **red**: run `36217723025` finished with **1 failed / 1660 passed**. The failure is `tests/test_product_webapp.py::test_cross_league_switch_never_serves_old_league_intelligence`, where the switched response reported `simulation_ready=True` instead of the expected fail-closed `False`.

Do not classify the directive complete or ask Management to test while this remains unresolved. Determine whether the assertion exposed actual cross-league readiness leakage or a race/test-contract issue caused by same-request completion of valid new-league intelligence. Preserve the underlying no-stale-cross-league contract either way, correct the implementation/test as required, and return main CI to green.

The live deployment currently restores the existing FSFFL league/state with `forecast=True simulation=False value=True complete=False` at startup. This is not yet production acceptance of the new supplement. After CI is green, perform the required current-State FSFFL rebuild and prove the first-party FUMBLES_LOST supplement is consumed, current player scoring becomes legitimately complete where required, and Simulation promotes. Persist exact production evidence before returning control.


## Post-PR #259 production acceptance regression — 2026-09-26
**State: ACTIVE — TWO-PLAYER FUMBLES_LOST COVERAGE GAP / SIMULATION REGRESSED**

PR #258 merged at `af8b854d79e689f484af4c5eab16c3abca1f0da9`. PR #259 merged at `85cb4254a418f21f2c788fc0d515d80bd8c102f3`; main CI is green and Render deploy `dep-darl4dt9fdbs73a28log` is live.

Production evidence is mixed and therefore acceptance remains open:
- at 2026-09-26T05:06:48Z, State `04f38468159c55d587a0aef6fc9eb4be997f3287dc02f3d03e703f09630ff505` reached legitimate FULL capability: 670 authoritative scored forecasts, zero partials, first-party FUMBLES_LOST supplement for 335 players, Forecast FULL, Simulation FULL, Value FULL;
- after a later fresh State sync at 2026-09-26T11:41Z, State `1a92ea28d0f66be7608442f1a1a3b3ea20da667409ef8fbbff894057050f214a` rebuilt from `live_full_season` evidence with 660 authoritative scored forecasts and **2 partial WR forecasts**. Simulation was correctly withheld with `partial_player_scoring_coordinates_present`;
- the two partial subjects are `sleeper:player:11630` and `sleeper:player:6149`; both omit only `fum_lost`. The first-party supplement contained 330 players and did not cover those two subjects.

This proves the architecture can restore full capability, but current production remains non-accepted because a fresh valid State can still introduce active offensive subjects outside the first-party supplement's mapped/current population.

Next corrective: explain and close the two-player supplement coverage gap generically without fabricating zero or special-casing player IDs; preserve degraded/fail-closed semantics where evidence truly cannot be established. Then rerun current-State FSFFL acceptance and cross-league/non-consumer regression. Stop only after production remains FULL on the current State or at a genuine permitted blocker/gate.


## Management clarification — localize the two-player coverage gap
**State: ACTIVE — GENERIC SUBJECT-UNIVERSE RECONCILIATION / PRODUCTION ACCEPTANCE**

Management rejects treating one missing coordinate for two players as a system-wide failure. Preserve fail-closed semantics, but localize incomplete authority to the smallest affected subject/consumer scope.

For the current FSFFL State, first-party FUMBLES_LOST generation must reconcile against the current canonical forecastable offensive subject universe and apply the accepted model tiers generically. Do not limit supplement generation to only subjects already present in a provider Forecast batch. Reuse the frozen model's deterministic identity recovery, history-only/current-only/cold-start/identity-light logic and non-zero uncertainty exactly; never substitute zero.

Current acceptance focus:
1. explain why `sleeper:player:11630` and `sleeper:player:6149` were omitted from the 330-player supplement while present in canonical State;
2. fix the generic population/reconciliation rule, not those IDs;
3. prove current canonical offensive subjects that satisfy the accepted model contract receive FUMBLES_LOST evidence even when provider-forecast membership changes;
4. distinguish truly unresolved subjects from merely provider-absent subjects;
5. make consumer readiness subject-aware: unrelated State/Forecast/Value/surfaces remain available, and Simulation blocks only when an unresolved subject can materially affect simulated outcomes under the current consumer contract;
6. rerun current-State FSFFL, Hodor, arbitrary-league, switch/restart and non-`fum_lost` regressions;
7. merge/deploy and prove the current production State remains FULL Forecast + Simulation after a fresh sync/rebuild before returning control.

Do not add a new heuristic, player special case, silent zero, or broad authority downgrade.


## Management correction — Simulation gates on its actual subject dependency set
**State: ACTIVE — CONSUMER-SCOPED READINESS CORRECTIVE / PRODUCTION ACCEPTANCE**

Production inspection confirms the two current partial `fum_lost` subjects (`sleeper:player:11630`, `sleeper:player:6149`) are unrostered in the current FSFFL State. Current runtime nevertheless adds `partial_player_scoring_coordinates_present` whenever *any* partial fantasy-point forecast exists, making universal Forecast incompleteness a league-wide Simulation blocker.

Correct this generically:
1. derive the Simulation-relevant subject set from the exact current consumer dependency graph (at minimum every rostered player the Simulation/lineup engine can actually use; include other subjects only where the consumer explicitly models their entry);
2. compute material-coordinate Simulation blockers only for partial subjects inside that dependency set;
3. preserve partial Forecast rows and explicit omission reasons for unrostered/unrelated players;
4. keep universal player-surface readiness separate from roster-based Simulation readiness;
5. do not special-case the two current player IDs, do not zero missing `fum_lost`, and do not weaken authority for rostered players;
6. add regressions proving: unrostered partial player does not block roster Simulation; rostered materially partial player does block; non-`fum_lost` leagues remain identical; switching/restart does not leak readiness;
7. deploy and perform a fresh current-State FSFFL sync/rebuild. Acceptance requires Simulation FULL despite these two unrostered player-specific partials, with those partials still truthfully visible on player/free-agent surfaces.

After this consumer-scoped readiness correction, separately continue the generic first-party supplement population reconciliation so provider membership changes do not unnecessarily omit otherwise model-eligible subjects.


## PR #260 production acceptance checkpoint — 2026-09-26 09:12 ET
**State: ACTIVE — FSFFL FULL RESTORED / CROSS-LEAGUE DURABLE-CHECKPOINT FAILURE REMAINS**

PR #260 merged to main at `bc16ebea6126b4b182adf9b9c5e9b3542031e54d`; post-merge main CI is green. Render deploy `dep-darruh8u01pc73dlh3l0` is live on that exact merge.

Fresh production acceptance after deploy proves the original FSFFL restoration objective is now functioning on the current State: Forecast FULL, Simulation FULL, Value FULL, overall FULL; no material partial-player blockers; first-party FUMBLES_LOST v4 reconciled to a canonical subject universe of 827 players with zero omitted subjects in the accepted FSFFL snapshot.

The acceptance sequence then failed at the **Hodor switch durability checkpoint**, not at FSFFL Forecast/Simulation authority. Exact production error at ~09:11 ET: `FSFFL persistence checkpoint timed out user=state-first-acceptance-20260926`, followed by `StateFirstAcceptanceError: hodor_switch canonical State did not durably checkpoint`.

Next corrective is therefore narrow: diagnose/fix the Hodor switch persistence checkpoint timeout without regressing the now-restored FSFFL FULL state, then rerun the entire FSFFL → Hodor → FSFFL State-first acceptance sequence and restart preservation. Do not reopen FUMBLES_LOST model authority or subject-scoping work unless new evidence proves regression.


## PR #261 post-deploy acceptance failure — exact-State supplement binding
**State: ACTIVE — CROSS-LEAGUE EXACT-STATE PERSISTENCE CORRECTIVE**

PR #261 merged at `c57bc394986ce871ceca672efaacb54f1346eed0`; post-merge CI is green and Render deploy `dep-dart6rgu01pc73dq4500` is live.

Fresh production acceptance again proves the existing FSFFL league itself reaches FULL Forecast + Simulation + Value. The cross-league sequence still fails after that success. The previous generic checkpoint timeout has narrowed to an exact-state binding failure while switching: `FSFFL persistence checkpoint failed ... first-party FUMBLES_LOST supplement does not match persisted State`, followed by `Synced Sleeper State could not be durably checkpointed`.

Do not reopen completed FUMBLES_LOST model or subject-universe work. Diagnose why the supplement/state pair being checkpointed during the Hodor switch is not bound to the same canonical State generation, preserve no-stale-cross-league guarantees, and rerun FSFFL → Hodor → FSFFL + restart acceptance before asking Management for full physical testing.
