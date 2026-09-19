# NEXT-2 Forecast Engine — Working Status

NEXT-2 is under active development.

Implemented so far:
- provider-neutral forecast observations and uncertainty distributions;
- point-in-time forecast metadata and provenance;
- replaceable forecast-provider boundary;
- deterministic equal-weight ensemble baseline;
- historical point-forecast scoring primitives;
- synthetic tests for ensemble and scoring behavior.

The equal-weight blend is a baseline comparator only. It is not production authority and must not be promoted merely because it is simple or stable.

Next work:
- point-in-time forecast snapshot/repository semantics;
- historical outcome matching and evaluation datasets;
- aggregation of forecast accuracy by provider, position, horizon, and metric;
- calibration/coverage testing for forecast uncertainty;
- evidence-derived ensemble challengers and out-of-sample validation;
- source licensing/provenance review;
- age/development and multi-year forecast treatment;
- formal NEXT-2 exit review.

NEXT-2 exit gate remains: forecasts can be evaluated historically and consumed without knowledge of source-specific payloads.
