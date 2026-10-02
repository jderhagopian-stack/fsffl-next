# 2026-10-02 — Origin-Aware Draft-Pick Value

## Status
**MANAGEMENT DIRECTIVE — FOUNDATION 3 ACTIVE AFTER #333 CLOSEOUT**

This directive implements Foundation 3 from `20260928_POST_STABILIZATION_FOUNDATION_SEQUENCE.md`.

Simulation 2.0 remains accepted. The 35k stress study does not reopen it; production authority remains **50,000** canonical runs. The Value work here must consume accepted Simulation outputs rather than recreate them.

## Objective
Replace generic year/round-only FSFFL draft-pick Intrinsic with a governed, distribution-aware coordinate for supported future picks:

`PICK_INTRINSIC = E[value(slot, draft_class, horizon)]`

The expectation must be taken over the **full team-of-origin exact slot distribution**. Do not value the expected slot itself. Pick-value curves are nonlinear, so `value(E[slot])` is not an acceptable substitute for `E[value(slot)]`.

## Authority boundaries

### Simulation owns
- team-of-origin slot probabilities;
- exact slot / expected slot / median / early-mid-late summaries;
- league draft-order mechanics and provenance;
- canonical 50k competitive uncertainty;
- common-world scenario mechanics.

Value must not infer team strength, standings, playoff order or draft slot independently.

### Value owns
- slot-specific economic value;
- draft-class strength evidence;
- horizon/time-to-realization adjustment;
- uncertainty composition;
- fallback economic priors when exact origin-aware valuation is unavailable;
- resulting typed pick-value estimate and provenance.

### Broad Market remains separate
Current provider-backed generic and early/mid/late pick market values are **Broad Market evidence**. They may be shown or used as explicit market evidence, but they do not become FSFFL Intrinsic merely because they are convenient anchors.

Do not overwrite the authoritative Broad Market Cardinal coordinate and do not force Intrinsic onto the market Cardinal scale without an already-governed conversion.

### League Market / Team Utility remain downstream
Do not introduce league willingness-to-pay, owner preference, roster need, recommendation or acceptance probability into this foundation. Those remain later layers.

## Existing primitives to reuse
The implementation should reconcile and reuse, not replace:
- `fsffl.value.pick.estimate_pick_value` and its exact probability-mixture moments;
- `PickOutcome`, `PickOutcomeSet`, `PickValueEstimate`;
- Historical Pick Coordinate evidence/logic, including structural draft-position dominance;
- accepted `TeamOriginFuturePickDistribution` from Simulation;
- canonical pick identity: `pick_id`, `original_team_id`, and separate current owner;
- existing Broad Market pick variants as a distinct market lens.

Do not create a second arbitrary pick scale or a second slot-probability model.

## Supported horizon
Authoritative origin-aware valuation is initially limited to draft seasons for which Simulation has a governed team-of-origin slot distribution.

At current accepted Simulation capability, that means the **next draft season**. Do not extrapolate an origin-team exact slot distribution into 2028+ merely because a pick exists.

Farther-future picks may continue to use an explicit generic year/round prior or remain unavailable under the current Value contract. Any fallback must be clearly identified as generic/non-origin-aware.

## Exact-slot economic coordinate

The worker must first inventory the currently governed slot-value / Historical Pick Coordinate evidence already in the repo and use the strongest defensible existing authority.

Requirements:
- exact slots are primary;
- earlier draft positions must weakly dominate later positions under otherwise identical conditions;
- no arbitrary hand-authored early/mid/late interpolation;
- no current-value-as-historical substitution;
- no future-information leakage into PIT evidence;
- evidence timestamps, source/model identity and uncertainty must remain explicit.

If current evidence cannot defensibly establish a full exact-slot economic curve for the target draft, implement the contract and return transparent partial/fallback status rather than inventing precision. A broad round/year prior is preferable to fabricated exactness.

## Draft-class strength
Draft-class strength is a Value-owned economic input, not a Simulation input.

Use only governed evidence that is actually available for the target draft class. Do not encode conversational reputation, analyst folklore or Management belief as a model coefficient.

If class-strength evidence is unavailable or too weak:
- preserve the governed baseline slot-value coordinate;
- mark class-strength evidence status/provenance explicitly;
- widen/retain appropriate uncertainty;
- do not fabricate a multiplier.

A factor of 1.0 is acceptable only when it semantically means “no governed class adjustment applied,” not “the class is proven average.”

## Horizon / time-to-realization
No arbitrary dynasty discount curve.

Reuse an existing governed horizon adjustment if one exists and is valid for the pick/as-of coordinate. Otherwise preserve the unadjusted economic coordinate with explicit status/provenance.

Uncertainty should not falsely shrink as the draft gets farther away. If a generic farther-future fallback is used, its uncertainty must reflect the weaker coordinate.

## Distribution and uncertainty
For each supported pick:
1. pair every Simulation slot probability with the governed value distribution for that slot;
2. use exact mixture moments through the existing Value primitive;
3. preserve both within-slot value uncertainty and between-slot uncertainty;
4. retain missing-slot/fallback status explicitly.

The authoritative mean is the probability-weighted slot value. The variance must include the mixture variance already handled by `estimate_pick_value`.

Do not collapse a wide slot distribution into a falsely precise “1.05” label.

## Origin and ownership semantics
The football slot distribution is keyed to the **original team**. The asset is held by the **current owner**.

A pure ownership transfer must not change the pick's origin-derived intrinsic value. It changes who owns the asset, not which team's finish determines the slot.

If a scenario changes the origin team's competitive roster, Simulation may legitimately change that origin slot distribution upstream; Value then recomputes from the changed Simulation evidence.

## Preview vs authoritative scenario values
The accepted Simulation progressive contract remains binding:
- 1k screening and 5k provisional outputs are non-authoritative;
- 50k confirmation or exact reuse of an authoritative canonical result is required for an authoritative origin-aware pick Intrinsic used by Decision/Opportunity action boundaries.

Preview Value may exist only if clearly labeled non-authoritative and kept behind the same downstream gates.

## Product/runtime integration
Expose the new coordinate where pick Value is already consumed, without broad UI redesign.

At minimum, the runtime/product contract should be able to distinguish:
- Broad Market pick value;
- FSFFL origin-aware Intrinsic pick value;
- generic fallback prior when origin-aware Intrinsic is unavailable;
- slot distribution / expected slot / uncertainty;
- original team vs current owner;
- exact provenance/model status.

Do not promote early/mid/late presentation summaries to economic authority.

Do not expand Search, Owner Intelligence or League Market in this workstream.

## Persistence / identity
An authoritative origin-aware pick Value result must be invalidated when any governing dependency changes, including as applicable:
- canonical Simulation result/model identity/count;
- State pick identity/original team/ownership;
- league/draft season/round;
- draft-order policy identity;
- slot-value coordinate/model version;
- draft-class evidence version;
- horizon-adjustment version;
- Value model/scale version.

Avoid recomputation when only current ownership changes and the economic inputs are otherwise identical; the asset/value result may be reattached to the new owner while preserving origin evidence.

## Required deterministic acceptance cases
Tests must prove at least:

1. **Nonlinearity**
   A nonlinear slot-value curve produces `E[value(slot)]` distinct from `value(E[slot])`; the implementation uses the former.

2. **Origin differentiation**
   Two same-season/same-round picks with different governed origin-team distributions can receive different Intrinsic values.

3. **Ownership invariance**
   Moving a pick between owners without changing origin/economic evidence does not change its Intrinsic value.

4. **Mixture uncertainty**
   A wider/bimodal slot distribution carries more between-slot uncertainty than a concentrated distribution with comparable mean slot, all else equal.

5. **Structural draft-position dominance**
   Earlier exact slots do not receive lower governed slot value than later otherwise-equivalent slots.

6. **Fallback truth**
   Missing exact-slot economic evidence yields a clearly typed generic/partial/unavailable result, not fabricated exact value.

7. **Season boundary**
   Do not apply next-draft Simulation probabilities to unsupported farther-future picks.

8. **Authority gating**
   1k/5k scenario Simulation cannot produce an authoritative downstream pick Intrinsic; 50k or exact authoritative reuse can.

9. **No circularity**
   Pick Value/Market does not feed back into Simulation team strength or draft-order probability.

10. **PIT safety**
    Historical/PIT evidence cannot use observations that were unavailable at the evaluation timestamp.

## Validation / promotion
This is a Value capability/model change. Apply the risk-proportionate validation protocol:
- focused deterministic tests for the exact Value contract;
- full CI;
- targeted downstream contract tests for Decision/product consumers touched by the implementation;
- bounded exact-head P1/P2 review;
- targeted hosted acceptance only if production runtime/persistence/product behavior is changed by the promoted slice.

Do not re-prove accepted Simulation 2.0 internals.

If implementation reveals that exact-slot economic evidence itself requires a new research model before promotion, keep that model in explicit Research/shadow status and continue implementing all non-fabricated contract/runtime pieces that can be completed safely. Return only the precise evidence gap to Management rather than parking the whole foundation.

## Closeout
Foundation 3 is complete when:
- supported next-draft picks have a governed origin-aware FSFFL Intrinsic coordinate;
- full slot distributions, not expected-slot shortcuts, drive the value;
- Broad Market / Intrinsic / later League Market remain separate;
- uncertainty/provenance/fallback semantics are durable;
- downstream consumers can distinguish authoritative origin-aware value from generic prior;
- required validation and any applicable hosted acceptance pass.

Then advance directly to **Long-Term Intrinsic**. Do not begin PIT historical-market expansion, League Market, Trade Decision or Search before this foundation closes.
