# NEXT-2 Forecast Engine Design Standard

NEXT-2 builds the forecasting layer that downstream valuation, simulation, trade, opportunity, and analytics systems will consume.

The objective is not to recreate a legacy projection system. It is to build a source-agnostic, historically testable, uncertainty-aware forecasting platform that can improve as evidence accumulates.

## Governing principles

1. Forecasts are point-in-time objects. Every forecast must be tied to what was knowable at a specific timestamp.
2. External projection sources are providers, not authorities. Their payloads are normalized before entering the core forecast layer.
3. Historical provider accuracy determines future trust where evidence is sufficient. Weighting may vary by position, forecast horizon, season phase, and statistic.
4. A forecast is a distribution, not just a single number. Central estimate, uncertainty, and relevant downside/upside information should travel together.
5. Ensemble construction must be evidence-driven. Equal weighting is a valid baseline, not an assumed optimum.
6. Aging, development, role, availability, and uncertainty effects belong in explicit components rather than hidden manual adjustments.
7. Forecast evaluation must prevent future-information leakage.
8. No downstream module may silently recreate player projections.

## Canonical forecast concepts

### ProjectionSnapshot

Represents a normalized provider projection captured for a player at a specific historical point.

It should identify:
- player;
- provider;
- forecast issue time / effective time;
- target season or horizon;
- projected statistics;
- projected fantasy points when scoring rules are supplied;
- provider/model version where available;
- provenance and licensing metadata;
- missingness and quality flags.

### ForecastDistribution

The authoritative FSFFL forecast output for one player and target horizon.

It should expose:
- expected outcome;
- median when estimable;
- uncertainty / dispersion;
- useful quantiles or downside/upside bands;
- probability of material availability where relevant;
- component/source contributions;
- forecast model version;
- evidence/calibration version;
- point-in-time input state reference.

### ForecastProvider

Adapters retrieve or ingest external projections and return normalized projection snapshots. Provider-specific field names must not cross the adapter boundary.

### ForecastModel

Consumes normalized historical/current evidence and produces `ForecastDistribution` objects. Multiple models may coexist as research/challenger models, but production authority for a given forecast responsibility must be explicit.

## Forecast horizons

NEXT should support more than one horizon rather than pretending one model is equally good everywhere.

Initial horizons:
- remaining/current season;
- next full season;
- multi-year dynasty horizon.

Longer horizons should explicitly widen uncertainty and rely more heavily on development/aging/role-risk treatment rather than false precision.

## Evaluation

Provider and model quality should be evaluated by position and horizon. Depending on the target, useful measures include:
- fantasy-points error;
- stat-level error;
- rank correlation;
- calibration of forecast intervals/probabilities;
- bias;
- stability across seasons;
- performance on meaningful player subgroups.

No single metric should automatically determine the best forecast source.

## Ensemble framework

The first implementation should include:
- simple mean baseline;
- simple median baseline;
- configurable weighted ensemble;
- historical scoring framework capable of learning/challenging weights later.

Weights must be versioned and evidence-backed. The architecture must permit position-, horizon-, and season-phase-specific weights without requiring redesign.

## Development and aging treatment

NEXT-2 should not bury career-curve assumptions inside source weighting.

Aging/development treatment should be explicit and testable, with the eventual ability to distinguish at least:
- position;
- age/career stage;
- experience;
- historical production/usage context;
- forecast horizon.

When evidence is weak, use bounded uncertainty-aware priors rather than unjustified precision.

## Uncertainty

Uncertainty should reflect more than disagreement among providers. Over time it may include:
- historical provider/model error;
- source disagreement;
- player volatility;
- role/usage uncertainty;
- injury/availability uncertainty;
- age/development uncertainty;
- long-horizon uncertainty.

The first implementation may begin with simpler empirically testable components, but the interface should support richer decomposition later.

## Historical testing rule

A historical forecast evaluation may use only information that was reasonably available at the forecast timestamp. Current projections, current market values, later injuries, later depth-chart changes, or realized outcomes may be used only as evaluation targets, never as historical inputs.

## NEXT-2 exit gate

NEXT-2 is complete when:
- provider projections can be normalized into canonical point-in-time snapshots;
- FSFFL can produce a source-agnostic forecast distribution;
- at least baseline ensemble methods are implemented;
- forecasts can be evaluated historically without future leakage;
- uncertainty is represented explicitly;
- provider/model performance can be compared by position and horizon;
- downstream code can consume forecasts without knowing which provider supplied the inputs;
- tests and CI enforce these guarantees.
