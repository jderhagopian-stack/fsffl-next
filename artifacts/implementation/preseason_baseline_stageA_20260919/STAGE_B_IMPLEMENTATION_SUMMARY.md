# FSFFL NEXT - Stage B preseason Year-1 authority implementation

Date: 2026-09-19  
Validated implementation head: `a0648e1b0f4d03569bf2f6c098f7c81b3878630b`

## Purpose

Complete only the source-authority correction authorized after Stage A recovered and verified the exact production preseason baseline.

## Implementation

1. `src/fsffl/forecast/preseason_baseline.py`
   - Defines `PRESEASON_AUTHORITY_RUNTIME_VERSION`.
   - The preserved baseline materializer is executable as an explicit authority coordinate.

2. `src/fsffl/product/forecast_resilience.py`
   - Adds `make_preseason_baseline_authority_loader`.
   - This loader reads the preserved baseline only and never calls live providers.
   - Missing/invalid baseline fails closed.
   - The existing resilient/live loader remains separate and live-first for the ordinary current Forecast path.

3. `src/fsffl/product/private_beta_shapley_runtime.py`
   - Frozen Intrinsic Year 1 is supplied by the explicit preserved-baseline authority loader.
   - It no longer inherits whichever evidence happens to occupy `context.forecast_evidence`.
   - Wrong/missing evidence basis fails closed.
   - Baseline evaluation time, runtime version, and evidence basis are added to explicit provenance.

4. `src/fsffl/product/persistent_webapp.py`
   - Wires the production persistence-backed baseline authority loader only into the frozen Shapley/Intrinsic consumer.
   - Leaves the general live/current Forecast loader intact.

5. `src/fsffl/value/live_intrinsic_calendar.py`
   - Labels the Year-1 authority `preserved_preseason_year1_forecast` when the source is the preserved baseline.
   - Live/current evidence retains its separate authority label.

## Regression evidence

Focused bounded regression workflow:
- Run: `35444335811`
- Result: **25 passed in 3.08s**

Repository CI:
- Run: `35444335817`
- Result: **1223 passed, 2 warnings in 8.61s**

The tests explicitly execute the concrete materialization path and verify live-drift quarantine, baseline/current provenance separation, and fail-closed behavior.

## Boundaries preserved

- No Forecast refit or redevelopment.
- No I1 / P0 / D0 / D1 changes.
- No Shapley algorithm changes.
- No C=0.25, 0.85 discount, B4, or Constitution changes.
- No provider-weight changes.
- No fresh provider fetch used as a substitute.
- No merge.
- No deployment.
