# FSFFL NEXT — Intrinsic Semantic Fingerprint Corrective

Updated: 2026-09-27

## State
**MANAGEMENT GATE — PHYSICAL DEVICE ACCEPTANCE**

The implementation, repository acceptance, exact Render deployment, and isolated hosted repeated refresh/switch validation are complete. A physical iPhone/Safari acceptance pass remains a distinct required promotion layer under OPERATING_PROTOCOL.md.

## Trigger
PR #268 was merged/deployed and passed deterministic dependency-scoped reuse tests, but production then persisted five separate ready 335-player Intrinsic contracts in roughly eleven minutes.

Root cause:
`intrinsic_input_fingerprint` still hashed volatile point-in-time and audit metadata, including Year-1 `as_of`, observation period timestamps, full provenance, runtime `evaluation_as_of`, Future Forecast provenance and evidence-path metadata. Mathematically identical governed Forecast content therefore acquired different cache identities after fresh State/Forecast loads.

## Corrective PR
PR #269 — `Intrinsic: stabilize compatibility fingerprint on semantic inputs`

Accepted head:
`6ce530762de4529183845e25d4dc11e3b8e6f249`

Merge:
`e4a603b2d197cd271a05b11642e37730ecee353d`

Final configured validation:
- CI — success; 1,714 tests passed;
- Private-beta Intrinsic live diagnostics — success;
- PR164 focused corrective regression — success;
- Live Forecast corrective trace — success.

The first PR run had two test-only defects (missing import of the frozen permutation constant and a fixture that overwrote the model-version mutation). Both were corrected without changing production authority behavior.

## Semantic compatibility identity
The production Intrinsic fingerprint now includes only inputs that can change the frozen Shapley result or its governed authority identity.

Included Year-1 semantics:
- player id;
- position;
- metric;
- horizon;
- fantasy-point mean;
- stable Forecast source;
- stable Forecast model version.

Included Year-1 authority:
- evidence basis;
- sorted independent source ids;
- current runtime model version.

Included Future Forecast semantics:
- Future Forecast contract version;
- evaluation season;
- scoring coordinate;
- Forecast model version;
- Forecast source;
- player id / position;
- year index / target season;
- central expectation;
- uncertainty kind;
- scenario id;
- scenario probability;
- scenario fantasy points.

Included league/model semantics:
- evaluation season;
- team count;
- lineup contract;
- scoring rules;
- Shapley Intrinsic contract version;
- Shapley Intrinsic model version;
- frozen discount;
- frozen seed;
- frozen permutation count.

Explicitly excluded from cache invalidation:
- Year-1 `as_of`;
- Year-1 period start/end timestamps;
- Year-1 retrieval/effective provenance timestamps;
- other non-mathematical Year-1 provenance metadata;
- runtime `evaluation_as_of`;
- Future Forecast provenance dictionaries;
- Future row `evidence_path`;
- other runtime trace/audit metadata;
- Year-1 stddev, which is not consumed by the current frozen Shapley adapter.

These excluded fields remain intact on Forecast and persisted Intrinsic artifacts for PIT/audit purposes. They are excluded only from compatibility identity.

## Deterministic acceptance
Regression coverage proves:
- fresh mathematically identical governed Forecast content with changed PIT timestamps/provenance produces the same fingerprint;
- source-id ordering does not change the key;
- a second loader on a fresh State reuses the same persisted contract and does not create a second persistence row;
- Year-1 numerical mean changes invalidate;
- Year-1 Forecast/runtime model identity changes invalidate;
- Future scenario probability/value/expectation math changes invalidate;
- Future Forecast model identity changes invalidate;
- subject-set/player identity changes invalidate;
- scoring or lineup changes invalidate;
- evaluation season changes invalidate.

Model authority remains unchanged:
`FROZEN_SHAPLEY_PERMUTATIONS == 2048`.

## Exact Render deployment
Primary exact deployment:
- service: `fsffl-next-private-beta`
- deploy: `dep-das7l4gjo6nc73aiejag`
- commit: `e4a603b2d197cd271a05b11642e37730ecee353d`

For isolated hosted acceptance, Management's existing gated State-first runner was temporarily enabled. Render deployed the **same exact commit**:
- acceptance deploy: `dep-das7nb7pn0mc73f683kg`
- commit: `e4a603b2d197cd271a05b11642e37730ecee353d`

After evidence collection the acceptance gate was disabled again. Cleanup deploy:
- `dep-das7uknpn0mc73f74oc0`
- same commit `e4a603b2d197cd271a05b11642e37730ecee353d`.

## Hosted repeated-refresh / switch acceptance
Isolated acceptance user:
`state-first-production-acceptance`

Sequence:
1. FSFFL initial reconciliation;
2. switch to Hodor;
3. switch back to FSFFL;
4. manual FSFFL Refresh Intelligence #1;
5. manual FSFFL Refresh Intelligence #2.

Final runner result:
**PASS**

### FSFFL initial
State:
`b30da47f0e107ebb83d3dd5453b13cc32f6c9811787c9ce886ee3467c0be3807`

Capabilities:
- Forecast FULL;
- Simulation FULL;
- Current Value FULL;
- Intrinsic FULL;
- Intrinsic ready, 335 estimates;
- Future Forecast model `forecast-vnext-a2-burr-20260922`.

### Hodor switch
League:
`sleeper:1397623301961981952`

Acceptance preserved the existing truthful partial-authority semantics; no full Simulation/Intrinsic authority was fabricated merely to satisfy the switch workflow.

### FSFFL return
State:
`e584a0aaffde05c318f458949aaff0453a2ec7750c3e687d1a9f904281eb15a4`

Capabilities returned FULL, including Intrinsic ready with 335 estimates.

### Manual Refresh #1
State changed and core State/current intelligence legitimately rebuilt/reconciled.
Runner outcome:
`changed_state_rebuild_or_partial_reuse`.

After reconciliation:
- Forecast FULL;
- Simulation FULL;
- Current Value FULL;
- Intrinsic FULL;
- 335 Intrinsic estimates.

### Manual Refresh #2
State changed again and the same full capability result was reached:
- Forecast FULL;
- Simulation FULL;
- Current Value FULL;
- Intrinsic FULL;
- 335 Intrinsic estimates.

### Intrinsic reuse evidence
Across the complete acceptance window, searches returned **zero** new:
- `FSFFL Intrinsic phase future-contract`;
- `FSFFL Intrinsic phase shapley`;
- `FSFFL Intrinsic background build completed`

logs.

Therefore repeated fresh State/Forecast loads and the Hodor→FSFFL return did not launch repeated 2,048-permutation Shapley builds. Intrinsic stayed ready at 335 estimates while core State/current-Forecast identity legitimately advanced.

This is the intended separation:
- volatile PIT/current-runtime identity may change;
- core State-dependent layers may rebuild;
- mathematically identical Intrinsic inputs reuse one semantic compatibility identity.

## Non-regression
Unchanged:
- 2,048 Shapley permutations;
- Intrinsic model authority;
- Forecast ownership;
- Future Forecast contract ownership;
- league scoring authority;
- State-first league-sync behavior;
- current Forecast/Simulation/Value rebuild semantics;
- audit/PIT metadata retention.

No timestamps were stripped from artifacts and no source/provenance authority was weakened.

## Remaining acceptance
Physical-device acceptance is still required as a distinct layer.

Required physical target:
- iPhone/Safari;
- FSFFL fully supported league shows Intrinsic ready without repeated visible rebuilding during repeated Refresh Intelligence;
- FSFFL → Hodor → FSFFL switching preserves truthful capability readiness;
- Hodor remains partial where authority is partial;
- returning to FSFFL restores the ready 335-player Intrinsic view without a repeated long Intrinsic build;
- no stale cross-league presentation or false-green readiness appears.

**MANAGEMENT GATE — PHYSICAL DEVICE ACCEPTANCE**
