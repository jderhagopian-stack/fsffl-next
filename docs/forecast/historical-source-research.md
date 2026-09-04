# NEXT-2 Historical Projection Source Research

## Purpose

Identify projection sources that can support honest point-in-time historical evaluation without making FSFFL NEXT dependent on one commercial provider or on data we cannot lawfully retain or redistribute.

## Screening criteria

Every candidate source is evaluated on:

1. **Point-in-time recoverability** — can we tell what the source projected at the time, rather than only what it projects now?
2. **Coverage** — QB/RB/WR/TE, season/weekly/rest-of-season, and enough seasons to evaluate stability.
3. **Granularity** — underlying football stats are preferred to only one fantasy-point total because FSFFL supports arbitrary league scoring.
4. **Historical outcome matchability** — player IDs and periods can be aligned to actual NFL results without hindsight leakage.
5. **Update timestamp quality** — the source exposes or can preserve when a projection became available.
6. **Licensing / redistribution** — raw provider data may be usable for private research but still inappropriate to commit or redistribute publicly.
7. **Replaceability** — provider-specific logic stays in adapters; no source becomes model authority.
8. **Commercial-path safety** — terms must be reviewed before any later commercial launch even if private personal research use is acceptable today.

## Candidate source notes

### Razzball

Useful candidate for current and archived preseason/weekly/ROS projection research. Public pages document free preseason projections and date-stamped update behavior. Their model exposes many underlying stat components and describes historical backtesting of components.

Status: **INVESTIGATE / candidate adapter**.

Do not assume historical completeness or redistribution permission from public accessibility alone. Archive availability and terms need explicit review before using a large retained corpus or commercializing.

### FantasyPros

Useful as an aggregate/comparison source. Public documentation says NFL weekly projections aggregate several third-party sources. Their API exposes NFL projections and historical season parameters, but API access and downstream usage rights need to be treated as licensed-provider questions rather than as open data.

Status: **INVESTIGATE / licensed-or-research candidate**.

Because FantasyPros itself aggregates other projections, it must not be treated as statistically independent from every underlying source when ensemble weights are calibrated.

### nflverse / ffverse ecosystem

Strong candidate for open historical outcomes, player-ID mapping, and some historical fantasy ranking/projection datasets. The nflreadpy ffverse loader explicitly exposes draft, weekly, and historical rankings/projections sourced from the DynastyProcess/ffverse ecosystem.

Status: **PRIORITY INVESTIGATION for historical research backbone**.

Need dataset-specific license/provenance review before deciding what can be stored in this public repository. Outcome data and open identifier infrastructure should be separated from any third-party projection data with different terms.

## Data-acquisition design

Historical projection research should use this flow:

**Discover source → verify timestamp semantics → verify terms/license → acquire snapshot → preserve source metadata → normalize behind adapter → match to actual outcomes → evaluate → retain only what policy permits.**

A webpage that exists today is not automatically proof of what was knowable on an earlier date. For point-in-time testing, FSFFL must have a dated historical artifact, provider-supported historical query, archived snapshot, or another defensible availability record.

## Storage policy

The public FSFFL NEXT repository should contain:

- source adapters;
- schemas;
- evaluation code;
- synthetic test fixtures;
- source/licensing registry metadata;
- reproducible instructions where allowed.

It should not automatically contain copied historical provider projection tables. Raw or derived retained datasets should live in a separate data store governed by source terms and redistribution rights.

## Statistical safeguards

Historical weighting must account for:

- correlated sources / aggregators;
- missing-player bias;
- survivorship bias;
- position and horizon sample size;
- preseason vs in-season information differences;
- scoring-format effects;
- source update timing;
- repeated observations of the same player/season;
- uncertainty in estimated source skill.

No provider receives a permanent weight because of reputation. Weights are estimates with uncertainty and can change as evidence accumulates.

## Near-term execution order

1. Use nflverse/ffverse as the first open-data research path for outcomes, IDs, and any genuinely historical projection/ranking snapshots it exposes.
2. Build provider-agnostic historical snapshot ingestion around the existing forecast contracts.
3. Add a source registry that records licensing/research/redistribution status separately from predictive quality.
4. Prototype Razzball and FantasyPros adapters only after timestamp and usage semantics are clear.
5. Run the first source-comparison study on whichever historical sources pass the point-in-time and licensing gates.

This source shortlist is provisional. Predictive quality will be decided by historical tests, not by this research note.