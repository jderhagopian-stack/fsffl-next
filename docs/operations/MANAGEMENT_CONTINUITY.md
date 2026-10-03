# FSFFL NEXT — Management Continuity

## Updated
2026-09-28

## Management objective
First make the hosted product reliably usable. Then return immediately to the upstream foundation program that will make Market / Trade / Intelligence materially stronger.

Do not trade reliability for new capability. Do not restart completed Research. Preserve the authority chain:

Data -> Point-in-Time State -> Forecast -> Simulation -> Value -> Decision -> Search/Optimization -> Analytics/API -> Presentation

## Current stabilization state
The atomic-publication program is the sole product-critical path.

Completed / merged runtime corrections:
- #284 — atomic intelligence publication / read isolation;
- #285 — serialize managed-team publication race;
- #287 — restore published managed-team + generation identity on cold exact-State activation;
- #289 — deterministic managed-team hosted proof improvements.

Current corrective:
- PR #290 — `Close final atomic-publication acceptance edges`
- head: `3ac755799e3f9d7a91e7ecf947e9d95f084ae908`
- state: OPEN / mergeable
- focused validations: green
- full CI: RED, one deterministic failure

Exact CI result:
- 1 failed / 1,779 passed
- failure: `test_changed_state_restore_carries_only_team_matched_served_publication_generation`
- `restore_runtime_snapshot()` carries `served_publication_generation_id == "served-generation-a"`
- but `PersistentPrivateBetaRuntimeStore.restore_user()` constructs active `ServedIntelligenceSnapshot.publication_generation_id=None`
- therefore changed-State continuity still loses the served generation identity during active runtime restoration even when the team-matched persisted identity is valid.

This is not accepted as CI noise.

## Immediate Implementation requirement
1. Fix the exact served-generation propagation mismatch without weakening the team-match / same-league / different-State / visible-snapshot predicates introduced to close #288 review findings.
2. Keep the final publication sequence serialized against managed-team/league identity changes so team selection cannot delete an active working generation during checkpoint -> presentation promotion -> durable publication -> in-memory swap.
3. Full CI green.
4. Merge the corrected exact lineage.
5. Deploy the exact merge SHA.
6. Run hosted FSFFL -> Hodor -> FSFFL plus same-State refresh, active-read overlap, cross-surface generation identity, managed-team change, interruption/restart and status/banner truth.
7. Only then return for physical iPhone/Safari validation.
8. Runtime stabilization closes only after physical validation.

No Forecast / Simulation / Value / Intrinsic semantic changes during this corrective.

## Physical acceptance expectation
On iPhone/Safari:
- Home, Franchise, League Atlas, Player Intelligence and Market load from one coherent published generation;
- a same-State intelligence refresh never makes previously valid Market / Intrinsic / Simulation data disappear merely because the replacement generation is mid-build;
- banner/readiness copy matches visible surface truth;
- one managed-team change survives refresh/restart;
- FSFFL -> Hodor -> FSFFL round-trip does not cross-contaminate generations;
- foreground reads remain usable while background reconciliation runs.

## Post-stabilization near-term development sequence
Execute only after runtime closure.

### 1. In-season current-year Forecast
Production:
- Actual YTD statistics/points are facts;
- governed third-party raw-stat ROS projections own the remaining-season expectation;
- FSFFL league scoring downstream;
- expected finish = Actual YTD + governed ROS;
- separate availability from conditional healthy production;
- no double-counting status/injury effects already embedded in ROS.

Prospective PIT ROS capture is perishable and should be preserved.

Native FSFFL ROS remains shadow Research until PIT comparison earns authority.

### 2. Simulation 2.0
Controlling directive:
`docs/operations/directives/20260928_SIMULATION_2_0_PROGRAM.md`

Bring forward / re-derive the strongest legacy capabilities:
- real league schedule and divisions;
- weekly player outcome distributions;
- legal week-specific lineup optimization;
- byes;
- explicit empty-slot behavior;
- availability / missed-game uncertainty and legal bench substitution;
- historical/player-position volatility with shrinkage;
- actual playoff qualification, seeding, byes and bracket rules;
- expected wins / points;
- full finish, playoff, division, bye, first-place and title distributions;
- deterministic replay seeds;
- governed counterfactual competitive-outcome deltas;
- replayable Multiverse worlds / unusual outcome examples.

Current-season engine:
- completed weeks are facts;
- future weeks are simulated from governed ROS distributions;
- preseason / current / forward outlook remain separate.

Performance architecture:
- canonical 50,000-run authority remains until convergence evidence changes it;
- compile static State once;
- vectorized/batched worlds;
- cache reusable lineup / substitution structures;
- common random numbers for A/B scenarios;
- dependency-based selective recomputation;
- persist exact State+Forecast+model results;
- ordinary page reads never rerun Simulation;
- progressive explicitly provisional scenario batches (~2.5k-5k screening -> 15k-50k confirmation);
- memory-bounded batching;
- no uncontrolled multiprocess expansion on the free-tier host;
- run 5k-100k convergence research before changing canonical 50k.

Simulation also owns future team-of-origin pick-slot distributions and competitive counterfactual deltas.

### 3. Origin-aware draft-pick Value
Simulation answers: where is this origin-team pick likely to land?
Value answers: what is that full slot distribution economically worth?

Preserve exact pick identity:
- year;
- round;
- origin team;
- current owner;
- actual league draft-order rules.

Use:
`PICK_INTRINSIC = E[value(slot, draft_class, horizon)]`

Value the full nonlinear slot distribution, not only the expected slot.

Separate:
- Broad Market pick value;
- FSFFL Intrinsic origin-aware value;
- future League Market evidence;
- downstream Team Utility.

Uncertainty widens with horizon. Generic year/round values are fallback priors only.

### 4. Long-Term Intrinsic
Resume the already accepted contract:
- Current Intrinsic = Y1-Y3;
- Long-Term Intrinsic = Y4-Y7;
- Y8 coarse only;
- separate 0-10,000 rulers;
- no arbitrary horizon weighting;
- preserve exact-vs-set-valued Forecast authority and uncertainty.

### 5. Historical / PIT market foundation
Build/strengthen:
- authoritative historical transaction ledger;
- historical PIT rosters / State;
- Historical Pick Coordinate with uncertainty/provenance;
- package structure/concentration evidence;
- contemporaneous Forecast/Value context where reconstructable;
- stable owner/team identity through seasons.

Do not substitute current values for historical values.

### 6. League Market + Owner Intelligence
Add the third economic lens:
- Broad Market;
- FSFFL Intrinsic;
- League Market;
- Team Utility downstream.

Owner Intelligence is evidence-based and directional:
- positional preferences;
- pick appetite;
- consolidation/diversification behavior;
- roster-construction tendencies;
- counterparties;
- package shapes.

No fabricated precise acceptance probability.

### 7. Trade Decision
Consume:
- legality;
- Broad Market;
- Current + Long-Term Intrinsic;
- League Market;
- team need / roster construction before and after;
- Simulation competitive deltas;
- contender/retool/rebuild context;
- pick timing / uncertainty;
- package concentration;
- bilateral counterparty effects.

Keep disagreements among dimensions explicit rather than collapsing into one opaque score.

### 8. Market / Search / Optimization
Only after the upstream inputs are mature:
- opportunity discovery;
- roster-aware package generation;
- bounded counters;
- market-test options;
- upgrade/downgrade paths;
- horizon / position targeting;
- owner-fit directional ranking;
- explain why the opportunity exists.

Search stays downstream of Decision.

### 9. Intelligence surfaces
Expose the matured foundations through North Star:
- Player Intelligence;
- Franchise;
- League Atlas;
- Owner Intelligence;
- Market;
- Trade Center.

## Work usage pattern
Use short read-only Work bursts as independent invariant reviewers:
1. architecture red-team before a substantial corrective;
2. focused adversarial PR review before merge;
3. exact-SHA DEPLOY/HOLD proof audit;
4. black-box cross-surface consistency audit after deploy.

Instruction principle:
**Prefer one violated invariant that explains a class of failures over many endpoint-specific symptoms.**

Work should not become a parallel implementation stream.

## Management preferences
- User wants the app usable before new model/features.
- After usability, robustness and foundational intelligence take priority over cosmetic feature work.
- Keep Management chat concise.
- Persist material Management decisions to `docs/operations/` before handing worker chats new scope.
- Prefer short continuation prompts.
- Watch chat length; when this Management conversation becomes unwieldy, start a new Management chat using this file + canonical operations docs as the handoff rather than recreating decisions from chat history.


## Post-stabilization use of Work for rapid execution
After runtime stabilization closes, Management may use short, explicitly authorized Work execution bursts to accelerate bounded capabilities whose authority contracts are already settled.

Work is appropriate for rapid implementation when all of the following are true:
- upstream authority and data contracts are already frozen;
- the capability has a narrow repo-bounded acceptance contract;
- no new empirical coefficient/model promotion is required;
- the change can be validated deterministically and rolled back cleanly;
- Work owns the exact branch/PR through tests, merge/deploy only when explicitly authorized.

Good near-term Work candidates:
- PIT capture / evidence persistence plumbing;
- Actual YTD + governed third-party ROS integration once provider contract is frozen;
- exposing already-governed Current / Long-Term Intrinsic outputs in product surfaces;
- exact provenance / diagnostics / publication metadata;
- bounded historical transaction / roster-state ingestion and normalization;
- presentation/API wiring for already-authoritative outputs;
- deterministic acceptance harnesses and regression coverage.

Use a slower Research -> directive -> implementation path for capabilities that create new authority or need empirical validation, including:
- Simulation 2.0 distribution/correlation/calibration changes;
- future multi-season team-strength / pick-slot forecasting;
- origin-aware pick-value curves if calibration is incomplete;
- League Market inference;
- Owner Intelligence behavior models;
- trade acceptance / decision coefficients;
- new Search/Optimization objective functions.

Preferred cadence after stabilization:
1. Management freezes a bounded directive and acceptance criteria.
2. Work performs a short implementation burst on current main / dedicated branch.
3. Independent review (Work or Codex) attacks the governing invariant before merge.
4. Merge/deploy exact SHA only when checks are green and the directive is satisfied.
5. Physical/product smoke where the capability is user-facing.

Do not let Work and the main Implementation stream modify the same authority surface concurrently. Parallelism should be by clearly separated workstream, not by overlapping code ownership.


## Latest stabilization delta — after PR #290
PR #290 merged as `213c95014155de698b25681244024f4a0a66aa6b` and full CI is green. The changed-State served-generation restore ordering issue is addressed. A post-merge P1 remains and is now the **only known stabilization blocker**: publication serialization is store-global and can deadlock against the store-global cold-restore lock across different users because the two paths acquire those locks in opposite order. Fix with per-user publication sequencing or a consistent lock order, add deterministic two-user concurrency coverage, then merge/deploy/hosted-accept/physical-smoke. Do not start the post-stabilization foundation program before this closes.


## Stabilization-management correction — stop calling each new defect “the last narrow fix”
Management recognizes that the repeated one-defect-at-a-time loop has produced false finish lines. The closeout strategy is now whole-class verification under `docs/operations/directives/20260928_STABILIZATION_CLOSURE_PROTOCOL.md`. The next corrective must close publication/persistence/restore/identity concurrency as a class, including deterministic two-user races and bounded stress, with pre-merge red-team. A bounded lifecycle/lock refactor is authorized if it produces simpler per-user ownership and consistent lock ordering. Do not deploy merely because the currently known P1 is fixed locally.


## User communication requirement
The product owner is not a software/computer engineer. Every chat in this project should default to plain-language explanations that let the user understand the product consequence and make informed decisions.

Use this order when discussing technical work:
1. **What happened / what we found** in normal language.
2. **Why it matters to the product or user experience.**
3. **What we are doing about it.**
4. **What remains uncertain or unproven.**
5. **What, if anything, the user needs to decide or do.**

Technical detail can follow, but should not be the primary explanation unless the user asks for it. Never assume familiarity with software-engineering concepts such as locks, race conditions, persistence, concurrency, threads, processes, caches, serialization, manifests, or dependency graphs; translate them when they matter.


## Latest stabilization delta — PR #291
The whole-class stabilization approach is now active in PR #291, head `7bcf6121688aa49f02cd4fbd4037925ca7d8503f`. The branch moves lifecycle coordination from one global lock to per-user coordination and adds deterministic two-user concurrency, restart/interruption and bounded stress coverage. Importantly, pre-merge review found adjacent issues **before deployment** (shared-league snapshot write ordering and idle worker accumulation), which is the behavior Management wanted from the new closure protocol. Current CI is 1 failed / 1,794 passed; the remaining failure concerns whether same-State checkpoint coalescing should durably write only the latest team context or also an initial State-only runtime pointer. Do not merge until that durability contract is explicitly resolved and CI/red-team gates are green.


## Latest stabilization delta — PR #291 merged
The whole-class stabilization corrective has now merged as `dbe7fccaceca525e0586389dcc5388764fa015a3`. The new process worked as intended: adjacent lifecycle defects were found and fixed before merge, full CI is green at 1,796 passed, deterministic single-user/two-user concurrency coverage and bounded stress are complete, and the pre-merge whole-class red-team found no remaining concrete P1/P2 lifecycle defect on the corrected head. Remaining gates are operational, not another planned code pass: deploy the exact merge SHA, complete hosted acceptance, then perform physical iPhone/Safari smoke. Do not start the post-stabilization foundation program until those two acceptance gates pass.


## Latest deployment status — #291
Exact merge SHA `dbe7fccaceca525e0586389dcc5388764fa015a3` is live on Render as deploy `dep-datdlnugekts73adssi0`. Hosted acceptance is currently running on the new instance. Initial FSFFL reconciliation and cross-surface publication consistency have passed so far, including PI history during active reconciliation; no terminal PASS/FAIL is recorded yet. Physical iPhone/Safari test begins only after terminal hosted PASS.


## Latest beta-availability incident — first-load regression
Physical iPhone testing after a surgical server-side reset proved the basic first-load path is regressed. The user's Sleeper submission was accepted, but Connect League remained visually inert for >1 minute; product-context reached ~51.6s; server State eventually persisted; browser-local saved team identity caused silent team restoration without an explicit choice; and the subsequent legitimate fresh Forecast acquisition did not reach a coherent published intelligence generation or surface a clear terminal failure.

Regression boundary is concrete: PR #54 (`0021aefc...`) / #56 (`a8527e1...`) intentionally made hosted connect usable once Sleeper State existed in memory, with persistence asynchronous and visible Safari progress. PR #261 (`c57bc39...`) later preserved a State-activation checkpoint wait while solving switch-safe durability, recreating blocking on first connect.

New controlling directive: `docs/operations/directives/20260928_FIRST_LOAD_REGRESSION_RECOVERY.md`. Restore the old responsiveness contract while keeping #261/#291 switch, atomic-publication, restart and durability safety. Do not ask Jimmy to test again until a controlled hosted true-clean first-run explicitly clears both server runtime state and browser-local state and passes connect -> explicit team selection -> State-only usability -> visible intelligence progress -> coherent publish or explicit failure.


## Latest architecture-audit disposition
Independent read-only Work audit confirms the founding analytical authority chain remains sound; the recent failures are primarily runtime/application architecture drift. One residual P1 exposure is now a formal stabilization gate: cold foreground `get()` can still invoke durable restore before fresh Connect activation, meaning persistence recovery can remain on the State critical path.

Controlling corrective: `docs/operations/directives/20260929_RUNTIME_ARCHITECTURE_AUDIT_CORRECTIVE.md`.

Target invariant: valid canonical State opens the league; persistence/restore are continuity mechanisms, not permission gates. Foreground `get()` should be an in-memory published read; durable restore should be explicit/outside fresh State activation and may install only if the captured runtime identity is still current. Preserve atomic publication, per-user sequencing, team identity guards and strict Forecast source-health authority.

PR #293 merged as `49ce8cae4f588fefc7c879e643504ee1b015cf42` and is currently under hosted acceptance. Let that run finish; then resolve any replay-scan P2 and the cold-restore/Connect architecture gate before declaring stabilization complete or requesting another iPhone/Safari test.


## 2026-09-30 — Active Simulation Work continuity checkpoint
Management has explicitly authorized the experimental, versioned NumPy/PCG64 batched-Gaussian Simulation path at the unchanged 50,000-trial count, subject to the separate production-adoption gate already recorded in `DECISION_LOG.md`.

Repo-visible Work state at this checkpoint:
- active PR: **#311 — [DRAFT] Study versioned batched Simulation RNG**;
- branch: `work/simulation-modernization`;
- repo-visible head: `6ef3fe9266c228b786a1cf5ab6ac915b057109e0`;
- production remains on the Python `Random.gauss` protocol / deployed #310 generation;
- the experimental RNG must not merge or deploy until Management reviews equivalence, replay, resource, downstream-behavior, CI/review, and hosted evidence.

Important continuity rule: GitHub silence alone does **not** prove that a Work session is stalled, because long benchmarks/equivalence studies can run before a commit is pushed. A successor Management chat must first reconcile the live PR/branch, current CI/reviews, canonical operations docs, and Render before deciding whether Work needs a poke. Do not reuse a stale continuation prompt blindly.

The current performance investigation also established a critical distinction for future profiling: the physical ~173.2s interval was measured from intelligence `job_start` at 11:22:57.729Z to `simulation_build_complete` at 11:25:50.938Z. Forecast was not rebuilt inside that interval on the observed run, and the heavy-work coordinator reported `active=behavioral` at job start. Render CPU was repeatedly at or near the 0.15 CPU service limit during the interval. Therefore ~173s must not be described as raw Monte Carlo draw time. It can include heavy-lane wait plus Simulation preparation, the 50k kernel, Team Utility/Analytics assembly, and contention from foreground work.

After the batched-RNG production decision, re-profile the **full hosted Simulation call** before choosing the next optimization. Required decomposition should separately measure at least: heavy-lane wait; lineup/static-state compilation; bye-aware weekly scoring/input construction; RNG; matchup/scoring; standings; playoffs; aggregation; Team Utility/Analytics; memory reclaim; persistence/publication. Continue the broader Simulation modernization by measured bottleneck order rather than assuming the Gaussian kernel is the whole ~173s problem.

If Work nears its session/context limit while authorized work remains, it must commit an exact handoff into `docs/operations/` with branch/PR/head, completed evidence, unresolved findings, current test/CI state, any Management gate, and the next executable action, then terminate as `TURN COMPLETE — CONTINUATION REQUIRED`. Normal Implementation should resume from that repo state rather than reconstructing from chat history.

## 2026-10-02 — Management continuity checkpoint: Simulation 2.0 item 8

Simulation 2.0 items #324 through #330 are accepted and must not be reopened absent contradictory evidence. The active implementation is **PR #331 — Simulation 2.0: add convergence and PIT calibration evidence** on branch `work/sim20-convergence-pit-calibration`.

Current management contract:
- production Simulation authority remains 50,000 runs unless Management explicitly approves a change;
- item 8 convergence/stability work may compare governed counts across 5k-100k plus preview context, but study evidence alone does not change runtime authority;
- PIT calibration is not a historical-data hunt. Use only authentic timestamped Forecast+State checkpoints already present and immediately identifiable;
- do not reconstruct old Forecasts, backfill current projections into old dates, scrape archives, or delay closeout looking for historical evidence NEXT never captured;
- if current realized PIT calibration coverage is too small, report the exact sample/coverage and close the slice as a prospective calibration framework that will strengthen as future snapshots resolve;
- counterfactual scenarios are tested for replay/stability/sensitivity, not unknowable alternate-world causal accuracy.

Latest repo-visible PR #331 status at this checkpoint:
- draft PR head `a2b87f03e9058a473c51a3b86b8011f785c00670`;
- convergence harness/workflow exists and is actively running;
- one pre-registered convergence workflow completed successfully while corrected/newer runs continued;
- recent CI on predecessor item-8 heads was green;
- PR currently needs reconciliation with newer main management commits before final review/merge;
- current evidence inventory reports **0 fully realized final-season PIT calibration cases** because the 2026 season is still active; this is expected and is not a blocker.

Accepted product direction to retain after Simulation 2.0 closeout:
- League Atlas should remain concise at league level;
- tapping a team opens a richer franchise drill-down with competitive outlook, full roster grouped by starters/bench/IR/taxi, player age/projection/Intrinsic/Broad Market values, draft capital, depth/fragility, origin-team pick distributions, Multiverse examples and provenance through progressive disclosure;
- actual/recorded lineup state and model-optimized/projected starters must remain semantically distinct.

Management continuity rule: keep this file and the canonical operations state current before chat context becomes a risk. A successor management chat should read `OPERATING_PROTOCOL.md`, `CURRENT_STATE.md`, `ACTIVE_WORKSTREAMS.md`, this file, and the current active PR before issuing implementation direction.

## 2026-10-02 — Simulation 2.0 item 8 / PR #331 CLOSEOUT: convergence stable, PIT framework prospective

PR #331 closes the final Simulation 2.0 evidence item. Items #324-#330 remain accepted and are not reopened.

Completed convergence evidence:
- successful pre-registered eight-root workflow run: `36999960485`, study head `9ec10864aca3a785baeab941d746fe114ca1ab36`;
- final artifact `11224026589`, digest `8116d174d9d6aef5bd9fa3c292c513718d2a98b8037337ff4b40a4f9372dbae8`;
- production 50k versus same-root 100k reference p90 errors: expected wins **0.014007**, playoff probability **0.002964**, championship probability **0.002427**, finish-distribution TV **0.005272**, future-pick-slot TV **0.005575**;
- clear and near-boundary expected-wins/playoff/title scenario-delta signs matched the same-root 100k reference for **8/8 roots**;
- 50k independent-root dispersion was small: expected-wins SD **0.004624** / range **0.01438**, playoff-probability SD **0.002317** / range **0.00732**, title-probability SD **0.000752** / range **0.00216**, future-pick expected-slot SD **0.011119** / range **0.04002**;
- three-run study-bundle median runtime was ~**24.23s at 35k**, **34.64s at 50k**, **51.86s at 75k**, and **69.09s at 100k** on the Actions fixture.

Interpretation:
- 50k is numerically stable for the governed fixture and materially tighter than lower counts while avoiding the additional runtime of 75k/100k;
- 35k is reasonably close, but this study does not establish a product/governance reason to reduce authority;
- 75k/100k reduce Monte Carlo error further, but the measured improvement is incremental rather than evidence that 50k is materially unstable;
- **production Simulation authority remains 50,000 runs**; no adaptive-count rule is promoted. Any future count change still requires separate Management approval.

PIT calibration closeout follows the explicit no-hunt rule:
- bounded existing-store evidence: **364** canonical State snapshots, **12** immutable provider ROS projection snapshots / **22,050** normalized observations, and **6** prospective football-state captures;
- authentic pre-opener Forecast artifact 63 exists but lacks a retained matching canonical State payload and is not reconstructed;
- earliest retained matched State+Forecast checkpoint is post-opener State `a7d56f...` + Forecast artifact 87;
- fully realized final-season Simulation calibration cases today: **0**; scored probability observations: **0**; scored continuous observations: **0**, because the 2026 season is still active;
- no historical Forecast reconstruction, current-projection backdating, archive scraping, or broader PIT discovery is authorized or required for closeout;
- the leakage-safe checkpoint/scoring framework is retained for prospective scoring as authentic 2026 checkpoints resolve.

Durable evidence:
- `docs/operations/evidence/simulation_item8_convergence_results_20261002.md`;
- `docs/operations/evidence/simulation_item8_convergence_summary_20261002.json`;
- `docs/operations/evidence/simulation_item8_pit_inventory_20261002.json`;
- reusable scoring/guardrail code in `fsffl.team_utility.simulation_validation`.

Promotion classification: research/evidence/framework only. This PR does not change production Simulation count, RNG, model authority, runtime/persistence identity, Decision authority, or accepted #324-#330 behavior. Therefore no Render deployment or physical acceptance is required for item-8 closeout; focused evidence/calibration tests + full CI + bounded exact-head P1/P2 review are sufficient.

**Simulation 2.0 program status after #331: COMPLETE.** The already-accepted post-Simulation sequence resumes with origin-aware draft-pick Value consuming the governed team-of-origin pick-slot distributions, followed by Long-Term Intrinsic and the later PIT historical-market foundation. Do not reopen Simulation 2.0 without contradictory evidence or a new Management directive.

## 2026-10-02 — #331 ACCEPTED: Simulation 2.0 convergence / PIT closeout

PR #331 was squash-merged as `505531ab389da80bd9837922113fe9888f18ff7c`. **Simulation 2.0 is complete.**

Final accepted item-8 evidence:
- exact PR head `102fffe8e50887f280730ef35bd0811dc2ec5e8f`;
- full CI **2,009 passed**, one existing warning;
- PR164 focused corrective regression PASS;
- completed eight-root convergence workflow run `36999960485`, final artifact `11224026589`, digest `8116d174d9d6aef5bd9fa3c292c513718d2a98b8037337ff4b40a4f9372dbae8`;
- 50k production error envelope versus same-root 100k reference remained small and all tested clear/near counterfactual delta signs matched across 8/8 roots;
- bounded manual exact-head P1/P2 review found no remaining issue after Codex review was unavailable because the account/repository code-review quota was exhausted;
- no Render deploy/physical acceptance was required because #331 is research evidence + calibration framework only and does not change production Simulation count, RNG, model/persistence identity, Decision authority, or accepted #324-#330 behavior.

Authority outcome:
- **production Simulation remains 50,000 canonical runs**;
- no adaptive trial-count rule is promoted;
- any future count change requires a new Management decision and its own implementation/promotion validation.

PIT outcome:
- authentic prospective 2026 State/Forecast inputs exist;
- fully realized final-season calibration cases remain **0** while the season is active;
- item 8 closes with the leakage-safe prospective calibration framework;
- no historical Forecast reconstruction, current-projection backdating, archive scraping, or broader PIT hunt is authorized.

Next approved program sequence: **origin-aware draft-pick Value** consuming the accepted team-of-origin pick-slot distributions -> **Long-Term Intrinsic** -> later **PIT historical market evidence**. Do not reopen #324-#331 absent contradictory evidence or a new Management directive.



## 2026-10-02 — Management follow-on: stress-test 35k before origin-aware Value

After accepting #331 and closing Simulation 2.0, Management elected to test the one genuinely plausible lower authority candidate rather than immediately moving on. The controlling directive is `docs/operations/directives/20261002_SIMULATION_35K_STRESS_TEST.md`.

This does **not** reopen #324-#331. Current production authority remains 50,000 runs. The bounded study compares 35k vs 50k under deliberately difficult governed cases, with same-root 100k as research reference. It must test not only numerical error but whether 35k changes product-relevant signs, rankings, classifications, pick summaries or downstream decisions where existing consumers apply.

Original item-8 context motivating the test: 35k three-run median ~24.23s versus 50k ~34.64s, while the original eight-root fixture preserved all tested clear/near delta signs. That evidence is promising but not broad enough by itself to change authority.

Temporarily hold origin-aware draft-pick Value until this gate resolves. If 35k is merely numerically noisier but product-equivalent across the stress set, return a Management proposal rather than changing production automatically. If any meaningful boundary case fails, retain 50k and resume the approved Value -> Long-Term Intrinsic -> PIT historical-market sequence.


## 2026-10-02 — 35k authority gate resolved

Management reviewed the completed 12-root / four-fixture stress study and retained **50,000** as canonical production Simulation authority. The candidate 35k count delivered ~29.9% median harness runtime savings but crossed materially more product-visible boundaries than 50k relative to the same-root 100k research reference: 71 candidate-only divergences versus 24 production-only divergences. Ranking agreement was 45/48 at 35k versus 47/48 at 50k; future-pick boundary summaries were 10/12 versus 11/12. Counterfactual signs/materiality remained stable at both counts.

Directive outcome: do not promote 35k, do not add an adaptive authority rule, and stop count hunting. 35k remains permissible only for explicitly non-authoritative research/internal use. Production remains 50k.

PR #333 is closeout-only and requires no Render/physical proof. Once merged, release the temporary hold and proceed immediately to **origin-aware draft-pick Value**, preserving the authority boundary: Simulation owns slot probability distributions; Value owns economic valuation; Decision remains downstream.


## 2026-10-02 — Foundation 3 activated: origin-aware draft-pick Value

The next management-controlled implementation is `docs/operations/directives/20261002_ORIGIN_AWARE_DRAFT_PICK_VALUE.md`.

Use accepted Simulation as an upstream probability source only. Value must reuse `estimate_pick_value` / exact mixture moments and reconcile the Historical Pick Coordinate rather than create a second pick scale or slot model. Provider generic/early-mid-late pick values remain Broad Market evidence, not FSFFL Intrinsic.

Authoritative scope begins with the next draft season because that is where accepted team-of-origin exact slot distributions exist. Do not extrapolate origin-team probabilities into later years. Missing class/horizon/slot economic evidence must produce transparent fallback/partial status rather than fabricated precision.

Required regression themes include nonlinearity, origin differentiation, ownership invariance, mixture uncertainty, slot dominance, fallback truth, season boundary, preview-authority gating, no circularity and PIT safety.


## 2026-10-02 — Narrow runtime corrective before Foundation 3 continues

A new physical run contradicted the accepted startup/reconciliation behavior. On live #330, one refresh reached `simulation_build_complete`, then logged `job_aborted` before publication; a replacement job rebuilt Simulation and downstream intelligence before 7/7. Peak RSS was 445,063,168 bytes versus the 429,496,720-byte engineering budget.

Management reopened only startup/manual-refresh lifecycle sequencing under `20261002_STARTUP_REFRESH_SEQUENCING_CORRECTIVE.md`. Do not reopen Simulation 2.0 semantics or reduce the 50k authority. PR #335 remains a valid safe checkpoint but is temporarily held. After the Tier-C corrective passes targeted hosted/physical acceptance, resume #335 immediately.


## 2026-10-02 — runtime corrective closed; Safari status defect deferred

The startup/manual-refresh sequencing corrective is accepted from physical + hosted telemetry. The winning physical refresh executed one State build, one 50k Simulation, Value, Intrinsic, and one terminal publication with no abort/restart. Peak RSS was **426,971,136 bytes**, below the **429,496,720-byte** engineering budget.

Management observed a separate user-facing issue: iPhone/Safari did not visibly acknowledge Refresh, show useful progress, or transition clearly to completed without a manual page reload. Park this as a future bounded browser-status/polling presentation effort. Do not let it trigger another acceptance-infrastructure chain and do not keep Foundation 3 on hold.

Resume PR #335 immediately from its pinned safe checkpoint, then continue the accepted Value -> Long-Term Intrinsic -> PIT historical-market sequence.

## 2026-10-02 — Simulation production performance diagnostic COMPLETE

The narrow production profile reproduced the current physical Simulation duration at ~127.8s while preserving 50,000 canonical trials, `numpy-pcg64-batched-gauss-v1`, and batch 500.

Measured hotspots are team-of-origin future-pick ordering (~27.558s), playoffs/championship (~15.824s), per-trial H2H reconstruction (~11.267s), and standings (~9.064s). RNG is only 1.481s; Multiverse is ~0.519s; cooperative foreground yield is ~0.192s. Team Utility / Analytics assembly adds 8.695s outside the 105.595s kernel.

Peak RSS was 388,489,216 bytes, below the 429,496,720-byte engineering budget and 536,870,900-byte Render limit. The service repeatedly reached its 0.15 CPU limit, so this is CPU-bound rather than memory-bound.

Management disposition: keep 50k authority and current RNG. The next bounded performance effort should first remove/batch-vectorize unconditional H2H reconstruction and reduce repeated Python work in exact team-origin slot ordering, preserving exact output/replay semantics; playoff batching is secondary. The earlier ~59s hosted NumPy interval is not an apples-to-apples current-workload baseline, while the current path remains ~26-27% faster than the ~173s legacy Python physical path despite richer Simulation 2.0 work.

Evidence: `docs/operations/evidence/simulation_production_performance_diagnostic_20261002.md`.

## 2026-10-03 — Simulation H2H performance tranche: code accepted, hosted benchmark pending Render rollout

Postseason PR #351 remains accepted and closed. Its controlling governed 50k benchmark is postseason **55.888s -> 8.836s** and kernel **104.901s -> 61.007s** with 50k/RNG/replay/model authority unchanged.

The next measured target was the NumPy-path per-world matchup/H2H reconstruction (~20.4s controlling baseline). PR #353 — `Simulation: batch H2H and Multiverse schedule products` — was squash-merged as `ea33d479a414bfa6a62ff06f7c4d84bdc8779e3b`.

Implementation:
- eliminates the second 50,000 × schedule Python scan in the NumPy production path;
- derives simulated H2H points plus Multiverse biggest-blowout/upset candidates inside the existing bounded 500-world schedule batch pass;
- precompiles H2H game-count topology once because scheduled games are world-invariant;
- leaves the legacy Python RNG path unchanged;
- preserves exact score generation and RNG consumption/order.

Correctness evidence at final PR head `c61aab7d6fb52e570e168d5ac6019d10257a2756`:
- full CI: **2,086 passed**, one existing warning;
- PR164 focused corrective regression: PASS;
- complete serialized/result equality against a literal scalar schedule-product reference across seeds 17, 2718 and 20261003;
- standing fixed 50k replay digest remained green;
- existing deterministic H2H/future-pick, 2/4/6/8 postseason, exact-provider, Multiverse/common-world coverage remained green.

Stale PR #349 was closed as superseded by accepted #351.

Hosted benchmark status:
- exact merged #353 deploy `dep-db05iiad0e5s73a6ijd0` built successfully and launched replacement instance `...-595zs`;
- the prior #351 instance shut down cleanly, but Render has not advanced the replacement deploy beyond `update_in_progress` and has emitted no Uvicorn startup/readiness/error after the launch command;
- a same-commit recovery deploy request was accepted as `dep-db05ksadails73995r9g` and is queued behind the stuck rollout;
- therefore **no #353 hosted 50k benchmark is yet valid**. Do not infer savings from CI or local structure and do not advance team-origin ordering until the governed hosted exact profile lands.

Next executable action: let Render resolve/cancel the stuck deployment lane, verify exact #353 is live, run one governed 50k exact profile, compare combined batch schedule-product + residual H2H cost and kernel/full-Simulation wall time against the accepted #351 baseline, then advance to team-origin ordering only if H2H has reached diminishing returns.


## 2026-10-03 — Management continuity checkpoint: performance + Foundation 4 + rollout

Current management intent:

- Keep Simulation authority at **50,000**; do not reopen trial-count/RNG/model semantics.
- Postseason optimization is accepted. H2H optimization is also materially proven in production: **20.355s -> 2.528s**, with the exact kernel now **43.487s** on the representative governed run.
- The next measured Simulation target is **team-origin future-pick ordering (~17.440s)** via PR #357.
- Do not declare H2H memory-safety closed until the post-merge #355 Codex P2 is fixed: release/reuse chunk storage so old + new dense H2H chunks/baselines cannot overlap beyond the intended bound.
- The runtime-availability acceptance failure observed after the successful profile is a narrow lifecycle/acceptance issue to root-cause separately; it does not reopen accepted Simulation semantics.
- Foundation 4 career-tail governance #352 is accepted. Empty draft #356 was closed and is not substantive implementation. Start the real holistic career-forward shadow implementation from current main.
- Product definition remains: **Current Intrinsic = separate Y1-Y3 lens; Long-Term Intrinsic = holistic career-forward value from today across all future years**, built from compatible raw economics rather than display-index arithmetic.
- After Foundation 4 passes shadow/persistence/API/resource acceptance, **pause the foundation-only cadence for one Product Integration / Capability Rollout tranche**. Put the accepted Simulation 2.0 competitive outlook, origin-aware pick intelligence and holistic Long-Term Intrinsic into the existing private-beta UI for the sole current user; use physical iPhone/Safari acceptance for the interaction/presentation change.
- Then continue to Foundation 5 PIT historical-market evidence while incorporating product feedback.
- Keep canonical `CURRENT_STATE.md`, `ACTIVE_WORKSTREAMS.md`, `MANAGEMENT_CONTINUITY.md` and the relevant workstream file updated at each acceptance/target transition; do not rely on chat history as durable authority.


## 2026-10-03 — Management continuity after #357/#358 and active #356

Current management handoff:
- #357 is merged. Hosted 50k target phase moved **17.440s -> 11.593s** for team-origin ordering; kernel measured **42.895s** on that run.
- #358 is merged/live and closes the outstanding H2H chunk-lifetime memory-bound P2 by reusing one bounded dense buffer instead of overlapping old/new chunks and a second baseline.
- Do not declare the Simulation optimization sequence closed until one fresh governed 50k run on #358 verifies current timing/RSS/output identity.
- The runtime-availability acceptance failure recurred after #357 publication while last-good surfaces were being served during an active newer generation. Treat this as a narrow lifecycle/acceptance issue; do not reopen Simulation 2.0 semantics.
- Foundation 4 draft #356 is substantive and green. It freezes the governed terminal artifact and implements the pure career-tail consumer + holistic raw career-forward aggregator. The current-authority CI job passed and emitted artifact **11261836244**.
- #356 is not yet Foundation 4 completion. Next: live cohort -> persistence/API -> restart/reload/resources -> bounded review/acceptance.
- Then execute the approved Product Integration / Capability Rollout tranche for the sole private-beta user before starting Foundation 5.
- Continue updating CURRENT_STATE, ACTIVE_WORKSTREAMS, MANAGEMENT_CONTINUITY and relevant workstream docs at each target/acceptance transition.


## 2026-10-03 — Management handoff after #359/#360

- #359 is merged but not fully closed from a management-quality perspective: fix the post-merge Codex P2 so **every** presentation surface must carry the expected publication generation during atomic last-good acceptance; missing generation IDs must fail closed.
- #360 is merged/live; obtain one governed 50k hosted profile before claiming further performance gains or choosing another target.
- Keep Simulation at 50k with exact RNG/replay/model semantics.
- #356 Foundation 4 is still the substantive implementation workstream and should continue in parallel; do not park it while optimizing Simulation.
- Foundation 4 completion path remains live cohort -> persistence/API -> restart/reload/resources -> bounded acceptance -> Product Integration / Capability Rollout -> Foundation 5.


## 2026-10-03 — Management continuity after successful #360 hosted run

- Exact live #360 completed governed 50k hosted acceptance: kernel **43.800s**, future-pick ordering **12.704s**, H2H **2.056s**, postseason **8.376s**, overall acceptance peak RSS **393,076,736 bytes**, runtime availability **PASS**, restored-refresh total **211.082s**.
- The Simulation kernel is now ~58.2% faster than the corrected **104.901s** baseline with 50k/RNG/replay/model authority unchanged.
- Do not claim #360 itself improved over #357 from one throttled-host run; #357 measured 42.895s kernel / 11.593s ordering. Treat the current performance band as ~43-44s kernel and re-profile only if pursuing another material optimization.
- The recurring last-good-during-rebuild acceptance failure was not reproduced: #359 path passed. Still close its post-merge P2 so any missing per-surface publication generation fails closed.
- Shift management emphasis back toward Foundation 4 #356. It is open/green but has not advanced since the shadow-contract/current-authority checkpoint.
- Next Foundation 4 gates: live cohort -> persistence/API -> restart/reload/resources -> bounded shadow acceptance -> Product Integration / Capability Rollout -> Foundation 5.


## 2026-10-03 — Intrinsic performance continuity note

Do not lose the previously identified Intrinsic optimization work. There are two distinct goals:
- **avoid unnecessary rebuilds** via dependency-scoped compatibility, durable persistence and exact restore/reuse; historical cold Shapley rebuilds were multi-minute;
- **speed the rebuild that is genuinely necessary** only after profiling the accepted Foundation 4 holistic path.

Recent hosted lifecycle evidence still puts the current Intrinsic phase at roughly **25–27s** when it runs. After #361 Foundation 4 correctness/persistence/hosted acceptance, run a bounded Intrinsic performance profile and optimize only measured material costs while preserving exact Current Intrinsic / Long-Term Intrinsic economics, fingerprints and restart identity. This should happen before or alongside Product Integration, not be forgotten behind the Simulation work.
