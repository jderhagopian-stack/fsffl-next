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
