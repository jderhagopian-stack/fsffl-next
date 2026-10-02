# 2026-10-02 — Foundation 4 Y4–Y7 Long-Horizon Shadow Component

## Status
**FOUNDATION 4 ACTIVE — BOUNDED NON-AUTHORITATIVE SHADOW**

Foundation 3 is accepted and closed. Simulation 2.0 and the deferred Safari-status UX issue remain closed/deferred absent contradictory evidence.

## Governing Research contract
Implementation consumes the already-accepted Long-Term Intrinsic research. Do not reopen model-family search.

This PR implements one bounded long-horizon component only:

`Y4_Y7_COMPONENT_RAW = (phi4 + phi5 + phi6 + phi7) / 4`

where each `phi_h` is the league-aware Shapley marginal lineup contribution for literal Y4, Y5, Y6 or Y7 under the governed Forecast authority for that year.

The divide-by-four operation is unit normalization inside this four-year component. It is not a discount or preference weight. **It is not the final product-facing Long-Term Intrinsic metric and must never be interpreted as holistic career-forward value.**

## Authority rules
- Current Intrinsic Y1-Y3 remains production authority and is not replaced or modified.
- The Y4-Y7 component is a separate non-authoritative shadow input to future Foundation 4 work.
- The eventual product-facing **Long-Term Intrinsic** must represent holistic career-forward value from today across all future seasons.
- This PR contains **no Y8+ value component**. Missing Y8+ authority is an evidence boundary, not a zero terminal value and not evidence that economic value ends at Y7.
- The final holistic metric must reuse compatible underlying Y1-Y3 Current Intrinsic economics plus this governed Y4-Y7 component plus a truthful governed Y8+ terminal/tail treatment.
- Exact Forecast cells remain exact:
  - QB Y5: `blanket_75_25`
  - WR Y5: `hard_router`
- Every other Y4-Y7 position×horizon cell preserves the frozen supported policy set.
- No hidden policy winner may be selected inside a set-valued cell.
- Raw Long-Term authority is a low/high envelope; its midpoint is a presentation/reference coordinate only.
- Model-authority uncertainty and within-model outcome uncertainty remain separately typed.
- No cumulative Long-Term standard deviation is authorized until cross-horizon covariance is governed.
- No Market, owner, team competitive window, trade/package context or manual youth/age/workload coefficient enters universal Long-Term Intrinsic.
- Separate 0-10000 display indexes are never additive or averageable. Any eventual Y1→career aggregation must operate on compatible underlying economic coordinates under an explicit governed aggregation rule.

## Implementation sequence

### Slice A — authority transport + pure Value consumer
Branch: `work/long-term-intrinsic-shadow`.

Add a Forecast-owned Y4-Y7 authority transport separate from the stable production Y2/Y3 `FutureForecastContract`:
- carry every frozen global policy board needed to reproduce the accepted research Shapley replay;
- preserve the frozen position×horizon supported-policy map by version/hash;
- reject Y8 cardinal rows.

Add a pure Value-owned Y4-Y7 long-horizon component consumer:
- use the existing governed lineup-capacity Shapley game;
- 2,048 permutations;
- deterministic horizon seeds;
- evaluate each global Forecast policy as one coherent league-wide board, exactly matching the accepted research replay;
- filter each player's annual Shapley records by its supported authority set;
- annual low/high = supported central Shapley extrema;
- four-year low/high = arithmetic mean of annual extrema;
- reference center = mechanical midpoint only;
- propagate annual 80/90 scenarios through Shapley and preserve combined outer bands;
- emit no cumulative SD;
- use a separate `fsffl-long-term-intrinsic-index:long-term-y4-y7-v1` within-lens rank ruler;
- keep the contract explicitly non-authoritative for product ranking.

### Slice B — governed runtime Y4-Y7 Forecast materialization
After Slice A is reviewed/accepted, port only the already-frozen Y4-Y7 Forecast authority required by the contract. Do not merge the old research branch wholesale and do not refit.

Required:
- current governed player universe;
- every frozen policy board used by the accepted authority map;
- annual central plus governed residual/conformal 80/90 evidence;
- exact policy/model/evidence lineage;
- authority-map identity;
- fail closed on missing player/horizon/policy coverage.

### Slice C — persisted Y4-Y7 component shadow + API
After the Forecast materializer is governed:
- persist the Y4-Y7 component separately from Current Intrinsic and from the future holistic Long-Term Intrinsic contract;
- stable semantic fingerprint excludes volatile timestamps;
- any shadow endpoint must be labeled as the **Y4-Y7 component**, not as final product Long-Term Intrinsic;
- ordinary Current Intrinsic endpoint/artifact remains byte/semantic unchanged;
- full current-cohort authority envelope and separate within-component display scale.

### Slice D — Y4-Y7 component acceptance
Before this component is accepted as an input to holistic Foundation 4:
- deterministic replay against accepted Research evidence;
- current full-cohort materialization;
- resource/performance acceptance;
- API/presentation validation;
- explicit Management acceptance of the component.

### Slice E — holistic career-forward Foundation 4
Foundation 4 is **not complete** at Slice D. Final product promotion additionally requires:
- reuse of governed Y1-Y3 Current Intrinsic economics as the near/mid-term component;
- reuse of the accepted Y4-Y7 shadow economics as the long-horizon component;
- a truthful governed Y8+ terminal/tail treatment;
- an explicit governed aggregation rule across compatible raw economic coordinates;
- horizon-preserving model-authority and outcome uncertainty;
- full live-cohort implementation, persistence/API shadow serving, resource acceptance, validation, and explicit Management promotion.

If Research does not govern Y8+ or the Y1-Y7 aggregation rule, implementation stops at that evidence boundary and opens the smallest required Research/governance slice. No arbitrary discount rate, horizon weight, age/youth multiplier, survival coefficient, or terminal-value assumption may be invented.

Market, Team Utility, Decision and live player ranking remain unchanged during the shadow phase.

## Product-definition correction

The internal code names introduced by this bounded PR may retain `LongTerm...` for continuity, but their governed semantics are **Y4-Y7 component shadow only**. They do not authorize a user-facing claim that Long-Term Intrinsic equals Y4-Y7, and they do not authorize setting Y8+ to zero.

Accepted Research establishes annual Y4-Y8 model-family evidence but explicitly leaves terminal/career semantics as a separate Management/governance question. Research also did not authorize a hidden master Intrinsic score. Therefore the next Foundation 4 slice must resolve the Y8+ tail and Y1-Y7 aggregation evidence boundary before holistic implementation can proceed.

## Validation rule
Apply risk-proportionate validation per slice. Slice A is a bounded new contract/pure Value capability with no live runtime behavior; focused Forecast/Value tests plus full CI and exact-head P1/P2 review are sufficient. Later runtime/persistence/product slices receive targeted hosted/physical acceptance according to their blast radius.
