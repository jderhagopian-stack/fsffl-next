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
