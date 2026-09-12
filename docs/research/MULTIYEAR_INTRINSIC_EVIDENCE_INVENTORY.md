# Multi-Year Intrinsic Value — Evidence Inventory

Status: research-only companion to `MULTIYEAR_INTRINSIC_VALUE_STUDY.md`.

This inventory classifies existing FSFFL NEXT evidence by the role it may play in the intrinsic-value study. It does not promote any model or coefficient.

## Existing evidence families

### Forecast / realized-outcome infrastructure

Available architecture already supports:

- point-in-time Forecast observations with as-of timestamps and provenance;
- chronological forecast backtesting infrastructure;
- multi-year career-transition evidence by position/cohort;
- survival probability separated from conditional production;
- multi-year annual forecast points with season offsets and cumulative survival/production metadata.

Use in intrinsic study:

- primary structural input;
- fitting evidence for replacement-adjusted football surplus and forecast-error calibration;
- uncertainty source;
- validation against realized future production.

Guardrail: Value consumes Forecast-owned distributions; it does not refit football survival or production itself.

### Market evidence

Available architecture already supports:

- current market observations from multiple sources;
- format-aware market context;
- normalized market percentiles;
- provider-native cardinal magnitudes;
- market-source benchmarking;
- market history snapshots/movement;
- point-in-time calibration metadata and source provenance.

Use in intrinsic study:

- auxiliary calibration evidence only where a specific economic parameter is identifiable;
- external validity / divergence analysis;
- held-out market-source diagnostics;
- independence-from-market testing.

Prohibited use:

- current market price as the sole dependent variable for intrinsic value;
- fitting a model whose practical objective is to reproduce market rankings/levels.

### Completed transaction evidence

Available architecture already supports:

- one-for-one trade observations;
- multi-asset package trade observations;
- transaction-price estimates;
- source-vs-transaction benchmark infrastructure;
- package-level transaction benchmarking.

Use in intrinsic study:

- candidate fitting evidence for intertemporal tradeoffs where current-production, age/horizon, and package structure can be controlled;
- candidate validation evidence for economic indifference/order consistency;
- evidence for discount/time-value estimation;
- evidence for optionality/nonlinearity challengers.

Guardrail: transaction evidence describes revealed exchange behavior and may contain market sentiment. It should identify bounded parameters or validate economic ordering, not become a direct target that collapses intrinsic into market clearing price.

### Draft-pick / future-asset evidence

Available architecture already supports:

- current pick values;
- early/mid/late pick variants;
- historical pick reconstruction;
- point-in-time historical pick evidence;
- pick outcomes;
- class-strength and slot-uncertainty concepts.

Use in intrinsic study:

- future-time preference evidence;
- optionality/uncertainty comparison;
- validation of long-horizon economic ordering.

Guardrail: current pick value should not be projected backward as historical truth.

### League rules / lineup structure

Available architecture already supports:

- team count;
- required lineup slots;
- FLEX/SUPERFLEX eligibility;
- scoring rules;
- optimized lineups;
- league-relative position strength.

Use in intrinsic study:

- structural derivation of league-level position demand;
- replacement population definition;
- format-specific scarcity.

Guardrail: focal-team roster need, contender status, and strategic posture remain downstream.

## Data still required / likely gaps

1. A reproducible historical panel joining, by as-of date:
   - player identity;
   - position;
   - league/format context;
   - point-in-time forecast distribution;
   - multi-year career state / transition evidence;
   - point-in-time market observations where available;
   - completed trade/package evidence where available;
   - subsequent realized production;
   - subsequent active/relevant status.

2. Historical league-wide eligible-player forecast universes sufficient to reconstruct replacement thresholds at each as-of date.

3. A clean transaction subset suitable for identifying intertemporal tradeoffs rather than simply mirroring contemporaneous market value.

4. A validation-only evidence partition that is never touched during parameter selection.

5. Historical survival-estimation uncertainty suitable for bootstrap/posterior propagation.

## Proposed evidence-role matrix

| Evidence family | Structural input | Parameter fitting | Validation | Must remain independent from target |
|---|---:|---:|---:|---:|
| Point-in-time Forecast | yes | yes | yes | n/a |
| Realized production | no | yes | yes | yes |
| League rules | yes | no | yes | n/a |
| League-wide player universe | yes | yes | yes | n/a |
| Completed transactions | no | selective | yes | yes |
| Market values | no | constrained/auxiliary | yes | yes |
| Pick exchanges/outcomes | no | selective | yes | yes |
| Team-specific need/posture | no | no | no | prohibited |

## Immediate build target

Before fitting Model B, build a research-only point-in-time row contract containing:

- `as_of`
- `asset_id`
- `position`
- `league_context_id`
- `forecast_model_version`
- annual forecast distributions by season offset
- replacement distributions by season offset
- realized future production by season offset where observable
- point-in-time transaction/market auxiliary evidence references
- provenance/evidence cutoff metadata
- fold assignment generated strictly from chronology

No model fitting should begin until the historical row builder can prove that every feature was knowable at its row’s `as_of` timestamp.
