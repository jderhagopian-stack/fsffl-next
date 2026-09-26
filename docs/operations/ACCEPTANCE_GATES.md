# FSFFL NEXT — Acceptance Gates

## Performance / intelligence lifecycle
Not complete until evidence demonstrates:
- durable last-good restoration;
- intentional mid-refresh restart behavior;
- stale-job reconciliation;
- truthful readiness state;
- no inappropriate automatic heavy refresh after restart;
- fresh 7/7 completion;
- atomic promotion;
- another restart surviving with the promoted last-good bundle intact;
- acceptable foreground latency during compute;
- Home, Franchise, and Market populated with governed evidence for the correct active league;
- no cross-league intelligence contamination.

Current status: **ACTIVE — MARKET FOREGROUND LATENCY ONLY.**

Evidence already satisfied for the existing FSFFL Dynasty incident:
- PR #222 fixes terminal failed/interrupted last-good restoration, same-league state-only demotion, restored-readiness precedence, and the mobile Refresh Intelligence grid/button;
- PR #226 is live on Render at `50614b1deeeccfe61c7b4fe3acc46111f7ad23cc`;
- production startup at 2026-09-25T13:52:35Z restored state `203227df...` with Forecast/Simulation/Value all present and `complete=True`;
- a second production restart at 2026-09-25T14:39:09Z restored the same complete bundle again;
- no automatic heavy intelligence job launched after either restart;
- PR #227 adds the interrupted-refresh restore regression and is merged/test-green;
- PR #235 / merge `3c252aed...` is live through Render deploy `dep-dar9kg142hec73dglcq0`; startup restored `jimmygoodjob` state `203227df...` with Forecast/Simulation/Value complete, no automatic heavy intelligence job and no startup errors;
- PR #235 removes request-local redundant Market input construction only. Repository-wide CI, PR164 corrective regression, and Live Forecast corrective trace are green, so PR #232 candidate admission, strategic-hypothesis, eight-path bilateral-screen, dominance/diversity, For You, and zero-broad-Simulation tests remain satisfied.

The jimmygoodjob last-good restoration evidence above is retained and must not regress. The separate Hodor/app-wide lifecycle corrective is now complete: PR #242 closed the Performance-owned State/lifecycle behavior, and Forecast PR #244/#245 subsequently populated durable shared Forecast + current Value while truthfully leaving Simulation absent under partial Forecast authority. Final Hodor restart evidence on Render shows `forecast=True simulation=False value=True complete=False` for State `d28de4cc...`.

Still open before Performance is complete:
- improve cold/focused Market foreground latency without weakening accepted Market discovery, Decision-screen, Forecast, or Simulation-authority semantics;
- preserve already accepted mobile lifecycle/state communication behavior.

The authenticated current-beta Market pass measured ~44.1s internal/~44.9s hosted cold automatic discovery and focused Target Player requests at ~31.8s, ~41.4s and ~47.8s, while a warm full workspace was ~0.137s. Foreground responsiveness therefore remains failed; CI or cache-hit evidence alone is insufficient.

## Forecast K/DST research
**Status: COMPLETE — RESEARCH / 2026 LATE-START PLAN READY.**

Research acceptance is satisfied by:
- `docs/operations/workstreams/RESEARCH.md`
- architecture: `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`
- empirical/source closeout: `artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_CLOSEOUT.md`
- 2026 late-start plan: `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`
- current-date source ledger: `artifacts/research/k_dst_late_start_exception_20260925/SOURCE_ACQUISITION_LEDGER.json`
- bounded empirical uncertainty results: `artifacts/research/k_dst_late_start_exception_20260925/EMPIRICAL_UNCERTAINTY_CHECK.md`

The completed research establishes:
- K as an individual-player Forecast family and D/ST as a team-unit asset;
- rule-level source independence and active-rule completeness;
- a one-season-only 2026 current-date ROS baseline exception with exact provenance and no backdating;
- explicit separation between current-forward 2026 authority and unavailable preseason comparison;
- subject-row source health against the real remaining NFL schedule;
- bounded empirical K and D/ST uncertainty measurements on explicit reduced scoring fingerprints;
- one current exact-capability provider candidate for Hodor-style 60+ K scoring and distributional D/ST PA tiers;
- no second public independent source yet proving those same hard coordinates;
- no Hodor-total uncertainty promotion from reduced fingerprints;
- no 2027+ late-start fallback.

No K/DST production coefficient or model authority is promoted merely by this research completion.

## New-league Forecast bootstrap research
**Status: COMPLETE — RESEARCH.**

The contract defines governed behavior for a league first connected after preseason:
- use an immutable league-agnostic annual raw Forecast snapshot when it exists;
- otherwise permit only an evidence-preserving migration of genuinely retained point-in-time raw Forecast evidence;
- preserve original timestamps, source identity, hashes, and lineage;
- do not refetch current pages and backdate them as preseason;
- fail closed on target scoring rules not supported by the retained raw evidence;
- when qualifying preseason evidence does not exist, surface preseason evidence as unavailable while permitting separately authoritative current-forward Forecast where valid.

## Forecast K/DST implementation gate
**Status: SHARED-FORECAST / PARTIAL-COVERAGE ACCEPTED — FULL K/DST AUTHORITY EXTERNALLY BLOCKED.**

PR #215 merged at `407c1bf85e5dc75f92b9906719f82bcd11d97c31` and established the base evidence-independent K/DST contract. PR #233 merged at `79c1f0c0aa094e4b1e3f6aa41eacd08c6bf1d6e8` and satisfies the first Management-authorized 2026 late-start implementation contract. PR #237 merged at `33b969b04180893f7e582c0ebd76c54bea81961d` and implements the second bounded private-beta exception: provisional current-ROS K/DST may expose only governed supported coordinates, with unsupported coordinates omitted and explicit partial-rule/provisional authority. Value/Simulation/Team Utility/Decision/Search may not silently consume it as full Forecast truth.


PR #244 merged at `edb9c0f9a1ccea4250761c63f65694d449c2d285` and restores the shared league-agnostic Forecast boundary. PR #245 merged at `7ad0d5ce4be038a2615433467227cdcfd3da85a4` and completes generic Sleeper acceptance plus truthful partial-authority lifecycle messaging. Final head `342f8c8e0ec4b0c8b1ffb5695abaf81ed98cb518` passed 1,620 full-suite tests plus all configured focused Forecast/Home/Atlas validations.

Production acceptance is satisfied for the corrective:
- Hodor no longer fails Forecast because its scoring includes unsupported coordinates;
- production emitted 330 explicit partial player-scoring outputs;
- Simulation was not promoted and reported `partial_player_scoring_coordinates_present` + `separate_k_dst_forecast_authority_required`;
- current Value became available;
- final Render deploy `dep-daredcl9fdbs7398s55g` restored Hodor State `d28de4cc...` with `forecast=True simulation=False value=True complete=False`;
- deterministic tests prove the same behavior across unrelated synthetic Sleeper league identities and materially different scoring profiles.

See `artifacts/implementation/hodor_shared_forecast_20260925/IMPLEMENTATION_HANDOFF.md`.

PR #238's exact-state safety hardening is already present on current main; the stale PR was closed unmerged after its six non-test implementation files were verified byte-identical to main.

Accepted code-level requirements already include:
- canonical K and D/ST subject identity;
- active-rule-complete scoring contracts;
- rule-level source-independence contracts;
- exact/derived kicker coverage without heuristic 50+ splitting;
- distributional D/ST bucket-scoring contract;
- deterministic K/DST realized-outcome and non-promoting calibration harnesses;
- immutable annual raw-snapshot replay;
- regression-clean no-K/no-DST behavior.

Management's 2026 exception changes the remaining acceptance gate:

### Cleared for current-forward 2026
- a K/DST baseline no longer needs pre-Week-1 provenance;
- a current-date ROS artifact may be acquired in 2026 if its real capture time, horizon, provenance and source-health are preserved;
- missing 2026 preseason K/DST evidence does **not** by itself block current-forward Forecast.

### Still unavailable
- any 2026 K/DST preseason comparison that lacks authentic pre-Week-1 evidence;
- the late-start artifact may never satisfy or masquerade as the annual preseason artifact.

### Empirical uncertainty evidence now available
Research has measured bounded reduced-fingerprint evidence:
- K season relative RMSE `0.3841884793`; weekly CV `0.5223274618`;
- D/ST sacks+INT season relative RMSE `0.2140283312`; weekly CV `0.6381941339`.

These are **research measurements only**. They are not accepted Hodor-total uncertainty coefficients because the fitted fingerprints exclude active Hodor coordinates.

### Current-forward Hodor blockers
Full-production K/DST authority remains unaccepted until evidence demonstrates:
- rights-cleared source access for the actual deployed provider set;
- >=2 independent healthy sources for each required subject/metric/horizon group;
- K: live validation of an exact 60+ evidence path plus a second independent 60+ source;
- D/ST: live validation of distributional PA-tier evidence plus a second independent PA-distribution source and remaining rare-event two-source coverage;
- target-compatible K and D/ST uncertainty promotion with explicit scoring-fingerprint compatibility;
- downstream Value/Simulation/Decision do not invent missing Forecast truth;
- successful new-league lifecycle acceptance under truthful downstream authority semantics.

These full-authority blockers do **not** erase the distinct 2026 provisional tier created by PR #237. Where qualifying rights-cleared current ROS evidence exists, Presentation/readiness/analytics may expose provisional K/DST with its omitted-coordinate and uncertainty limitations attached; downstream full-authority consumers remain blocked.

Already satisfied in PR #233:
- schedule-aware row freshness quarantines stale post-game ROS rows rather than backdating or heuristically adjusting them;
- the dedicated late-start artifact is hard-rejected outside 2026;
- research-only provider evidence and zero-uncertainty states cannot acquire production authority.

JerryGM is one technically exact-capability current ROS candidate:
- its docs support 60+ K custom scoring;
- its D/ST model exposes a PA spread and expected custom PA-tier value;
- its current ROS path is schedule-aware.
It remains an **external-access/rights candidate**, not production authority, until a live payload is validated and written usage rights permit FSFFL's derived multi-source Forecast use.

The controlling Research plan is:
`artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`.

## League-agnostic scoring coverage research
**Status: COMPLETE — RESEARCH / IMPLEMENTATION PLAN READY.**

Research acceptance is satisfied by:
- `artifacts/research/scoring_coordinate_coverage_20260925/SCORING_COORDINATE_REGISTRY.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/SCORING_COORDINATE_REGISTRY.csv`
- `artifacts/research/scoring_coordinate_coverage_20260925/PLATFORM_COVERAGE_MATRIX.csv`
- `artifacts/research/scoring_coordinate_coverage_20260925/PRIMARY_SOURCE_LEDGER.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/GAP_ANALYSIS.md`
- `artifacts/research/scoring_coordinate_coverage_20260925/IMPLEMENTATION_HANDOFF.md`

The completed audit demonstrates:
- documented major-platform defaults/custom scoring were researched without treating configurability as prevalence;
- a provider-neutral coordinate registry and rule-semantics model are defined;
- current FSFFL State/Forecast/scoring/provider/history gaps are explicitly mapped;
- nonlinear rules are separated from scalar-mean scoring;
- IDP is identified as a distinct subject-family expansion;
- provider raw-field preservation and historical replay requirements are defined;
- FULL/PARTIAL/UNSUPPORTED capability semantics and reason codes are defined;
- deterministic cross-platform fixtures are specified;
- implementation is staged without promoting production authority.

## Scoring coverage Stage 0/1 implementation gate
**Status: MANAGEMENT GATE — NOT AUTHORIZED BY RESEARCH COMPLETION.**

If Management authorizes implementation, Stage 0/1 is accepted only when evidence demonstrates:
- canonical registry/rule/capability contracts are versioned;
- raw platform scoring rules remain preserved alongside compiled mappings;
- current FSFFL scoring outputs are regression-identical through the compatibility lane;
- unknown/custom rules survive import and become explicit UNSUPPORTED rather than disappearing;
- position predicates, thresholds, stacking and semantic-profile fields are representable even when Forecast evidence is not yet available;
- rights-permitted provider raw numeric fields can be retained before canonical reduction;
- an unmapped provider field can be preserved without acquiring scoring authority;
- PARTIAL capability never publishes an incomplete authoritative fantasy-point total;
- no new production Forecast metric, provider authority, uncertainty coefficient, IDP support, or nonlinear model is promoted by Stage 0/1.


## Forecast FUMBLES_LOST authority gate
**Status: RESEARCH ACCEPTED — FIRST-PARTY MODEL READY FOR IMPLEMENTATION / PRODUCTION ACCEPTANCE.**

Management superseded the external-provider-permission critical path with the first-party Forecast-model directive.

Research acceptance is satisfied by:
- `artifacts/research/fumbles_lost_first_party_model_20260926/MODEL_SPEC.md`;
- `artifacts/research/fumbles_lost_first_party_model_20260926/CURRENT_INPUT_ASSESSMENT.md`;
- `artifacts/research/fumbles_lost_first_party_model_20260926/PRODUCTION_READINESS_HANDOFF.md`;
- machine-readable OOT validation and shadows in the same directory.

Accepted Research model:
`next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate`.

Evidence:
- exact lost-fumble semantics only;
- chronological OOT folds 2023/2024/2025;
- combined primary OOT n=1,599;
- RMSE 0.8105 vs omission 1.0425 and position-game baseline 1.0475;
- bias +0.0509;
- zero-calibration gap 0.0347;
- current identity coverage 327/335 = 97.61%;
- non-zero position and cold-start residual uncertainty floors;
- model/features/gates frozen before 2026 named-player shadow inspection;
- no unrelated offense coordinate rebased.

Production acceptance is **not** satisfied merely by Research. Forecast/Product Implementation must demonstrate:
1. exact lost-fumble target semantics; total fumbles cannot substitute;
2. strict prior-season training and canonical completed-week current cutoff;
3. frozen 2026 scalar `0.6158756078393594` reproduced from governed pseudo-current evidence;
4. current input semantics exactly match the accepted opportunity definitions;
5. non-zero uncertainty floors and explicit degraded identity/cold-start tiers;
6. current State cutoff mismatch invalidates the model supplement;
7. the supplement is overlaid only into current player scoring;
8. retained preseason/ordinary offense raw Forecast content and identity remain unchanged;
9. no current first-party output is visible to an earlier PIT cutoff or 2026 preseason comparison;
10. missing/ambiguous model evidence never becomes a silent zero;
11. current FSFFL rebuild reaches legitimate full player-scoring authority before Simulation promotion;
12. existing Hodor/other-league partial-authority behavior does not regress.

Existing PR #253/#255 supplement plumbing remains the intended integration seam.

The external JerryGM + LineupExperts route remains fallback/benchmark only. It is no longer an acceptance prerequisite for the first-party path.

The auxiliary single-source tier remains irrelevant because this is a Forecast-owned empirical model, not a one-provider authority exception.


## Intrinsic long-horizon comparative Research gate
**Status: MANAGEMENT GATE — NO MODEL-FAMILY BREAKPOINT PROMOTED / NO PRODUCTION AUTHORITY.**

The expanded six-family chronological Y4-Y8 study supersedes the earlier H5-centered gate.

Research selection:
- annual post-H3 Research family: `two_part_state` for QB/RB/WR/TE at Y4-Y8;
- empirical model-family breakpoint: **none**;
- position/horizon model router: **not accepted**;
- survival/hazard: diagnostic/model-risk challenger only;
- career-state transition: terminal/persistence-state challenger only;
- production H3: unchanged.

Why routing is rejected:
- direct ridge wins MAE in 17/20 cells but RMSE/tail-RMSE in 0/20 through upper-tail compression;
- paired dynamic-route testing lowers MAE at later horizons while significantly worsening squared error;
- no challenger establishes stable multi-objective dominance sufficient to justify routing complexity.

Before any Y4+ cardinal production authority can be considered, a later Management-authorized package must clear:
1. PIT chronology and current identity/feature coverage;
2. per-position/horizon uncertainty and survival calibration;
3. cross-year covariance/scenario uncertainty for cumulative Value;
4. exact H3 semantic/output preservation;
5. Shapley deployment-game parity and efficiency;
6. cardinal-scale/discount governance independent of current-player aesthetics or market prices;
7. fail-closed handling where annual precision is too weak;
8. downstream containment: Market, Decision and Team Utility may consume promoted coordinates but may not manufacture or rewrite them.

The study does **not** establish that Y4-Y8 are equally precise merely because one family is retained. It also does **not** establish an exact terminal/career cardinal value.

Durable handoff:
`artifacts/research/intrinsic_y4plus_model_family_20260926/FINAL_CLOSEOUT.md`.

No Y4+ production implementation is currently authorized.

## Product principle
Do not make a red gate green by weakening model authority, fabricating projections, backdating evidence, or hiding unsupported assets in Presentation.


## Market / Trade Discovery architecture review
**Status: COMPLETE — MANAGEMENT ACCEPTED.**

Implementation-ready handoff:
- `docs/operations/workstreams/MARKET_DISCOVERY.md`
- `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`

Architecture review evidence demonstrates:
- the repeated-neighborhood failure mechanism in the current package-row-first Search;
- why additive Cardinal closeness is insufficient before Decision-owned package economics;
- why current sparse bilateral enrichment cannot support a multi-card high-signal feed;
- how OpportunityHypothesis → MarketOpportunity → CandidatePath separates strategic attention from package variants;
- how existing Decision primitives can supply bounded pre-Simulation screening without fabricated acceptance probability;
- how family clustering, dominance pruning, and diversity selection prevent repeated target neighborhoods from crowding For You;
- why exact changed-state Simulation remains downstream of a selected transaction;
- why global 7/7 and lazy all-player Intrinsic readiness are different contracts;
- how Player Board / Free Agents can render partial governed evidence without weakening fail-closed authority;
- a deterministic fixture/test matrix including repeated Gibbs neighborhoods and extreme Superflex package shapes;
- a bounded implementation/migration sequence.

Management accepted the architecture on 2026-09-25 and authorized the bounded implementation executed in PR #220.

## Market implementation acceptance gate
**Status: CURRENT-BETA CORRECTIVE IMPLEMENTATION SATISFIED NON-PHYSICALLY — PHYSICAL IPHONE / SAFARI GATE NEXT.**

PR #240 is merged at `7b7f44ef0b3bf22008d80a3363aec1e6ce6f19d9` and live on Render as `dep-darb4lid0e5s73e2nnkg`, static generation `20260925-market-beta-corrective2`.

Acceptance evidence now includes:
- competitive posture materially constrains early target admission from governed age/season-Forecast evidence where available instead of remaining order-only;
- deterministic fixtures demonstrate appropriate Win-now/Rebuild divergence and fail-open overlap when evidence is missing;
- selector changes are configuration-only and cannot automatically launch focused Search;
- **Find opportunities** is the explicit expensive-work boundary with visible running/stale/completed state and response-race guards;
- focused zeroes expose where the submitted neighborhood exhausted, with candidate/admission/package/economic/family/preliminary-screen/dominance/final counts;
- the eight-path preliminary Decision budget is unchanged and does not truncate cheap Search exploration;
- broad discovery remains at zero exact changed-state Simulation calls;
- Forecast, Broad Market and FSFFL Intrinsic availability are independent, with per-player reasons and Intrinsic build/coordinate diagnostics;
- mobile Board/safe-area/Free Agent/Player Intelligence corrective behavior remains covered;
- full CI, all configured focused product regressions and live Forecast trace passed.

Production deployment is healthy with no application errors. The process currently restores the separate Hodor/new-league Performance context with derived intelligence incomplete, so no authenticated PR #240 focused/value-lens request has yet exercised the new production diagnostics.

**Remaining acceptance:** repeat physical iPhone/Safari Market validation on a context with sufficient governed evidence, followed by inspection of the emitted focus/value-lens telemetry. Do not weaken Market or lifecycle authority if Hodor remains incomplete.
