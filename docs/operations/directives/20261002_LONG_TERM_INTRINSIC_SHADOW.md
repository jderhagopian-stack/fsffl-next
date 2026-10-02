# 2026-10-02 — Long-Term Intrinsic Shadow Implementation

## Status
**FOUNDATION 4 ACTIVE — BOUNDED NON-AUTHORITATIVE SHADOW**

Foundation 3 is accepted and closed. Simulation 2.0 and the deferred Safari-status UX issue remain closed/deferred absent contradictory evidence.

## Governing Research contract
Implementation consumes the already-accepted Long-Term Intrinsic research. Do not reopen model-family search.

The Long-Term Intrinsic economic coordinate is:

`LT_RAW = (phi4 + phi5 + phi6 + phi7) / 4`

where each `phi_h` is the league-aware Shapley marginal lineup contribution for literal Y4, Y5, Y6 or Y7 under the governed Forecast authority for that year.

The divide-by-four operation is unit normalization across four one-season coordinates. It is not a discount or preference weight.

## Authority rules
- Current Intrinsic Y1-Y3 remains production authority and is not replaced or modified.
- Long-Term Intrinsic Y4-Y7 is a separate non-authoritative shadow until explicit later promotion.
- Y8 contributes no cardinal Long-Term Intrinsic value.
- Exact Forecast cells remain exact:
  - QB Y5: `blanket_75_25`
  - WR Y5: `hard_router`
- Every other Y4-Y7 position×horizon cell preserves the frozen supported policy set.
- No hidden policy winner may be selected inside a set-valued cell.
- Raw Long-Term authority is a low/high envelope; its midpoint is a presentation/reference coordinate only.
- Model-authority uncertainty and within-model outcome uncertainty remain separately typed.
- No cumulative Long-Term standard deviation is authorized until cross-horizon covariance is governed.
- No Market, owner, team competitive window, trade/package context or manual youth/age/workload coefficient enters universal Long-Term Intrinsic.
- Current and Long-Term raw/index values are not additive.

## Implementation sequence

### Slice A — authority transport + pure Value consumer
Branch: `work/long-term-intrinsic-shadow`.

Add a Forecast-owned Y4-Y7 authority transport separate from the stable production Y2/Y3 `FutureForecastContract`:
- carry every frozen global policy board needed to reproduce the accepted research Shapley replay;
- preserve the frozen position×horizon supported-policy map by version/hash;
- reject Y8 cardinal rows.

Add a pure Value-owned Long-Term consumer:
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

### Slice C — persisted shadow + API
After the Forecast materializer is governed:
- persist `long_term_intrinsic_contract` separately from Current Intrinsic;
- stable semantic fingerprint excludes volatile timestamps;
- shadow endpoint `/api/value/long-term-intrinsic-v1`;
- ordinary Current Intrinsic endpoint/artifact remains byte/semantic unchanged;
- full current-cohort authority envelope and separate display scale.

### Slice D — shadow acceptance / later promotion gate
Before any product-authority promotion:
- deterministic replay against accepted Research evidence;
- current full-cohort materialization;
- resource/performance acceptance;
- API/presentation validation;
- physical mobile validation;
- explicit Management promotion.

Market, Team Utility, Decision and live player ranking remain unchanged during the shadow phase.

## Validation rule
Apply risk-proportionate validation per slice. Slice A is a bounded new contract/pure Value capability with no live runtime behavior; focused Forecast/Value tests plus full CI and exact-head P1/P2 review are sufficient. Later runtime/persistence/product slices receive targeted hosted/physical acceptance according to their blast radius.
