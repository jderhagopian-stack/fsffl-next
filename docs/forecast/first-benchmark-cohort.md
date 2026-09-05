# NEXT-2 First Multi-Source Historical Benchmark Cohort

## Objective

Run the first broad historical forecast study as one reproducible batch rather than as a sequence of provider-specific mini-projects.

The benchmark should compare multiple historical projection sources against one realized-outcome backbone, learn challenger weights only on earlier history, and evaluate all sources and ensembles on held-out later history.

## Cohort strategy

The first cohort is deliberately small enough to complete quickly and broad enough to test the architecture. The target is 3-5 viable projection sources. A source enters the scored cohort only when both of these are true:

1. a defensible point-in-time artifact or provider historical query exists; and
2. private research use has been reviewed sufficiently for the intended acquisition method.

Licensing/commercial suitability is tracked separately from predictive performance. A source can be excellent for private research and still require replacement or a commercial agreement later.

## Current candidates

### nflverse / nflreadpy

**Role:** realized outcomes and player identity backbone.

This is not a projection vote. It supplies the target that historical forecasts are scored against and helps normalize player identifiers. nflreadpy documents nflverse releases and dataset-specific licensing. Exact dataset rights must still be checked before retained or redistributed data is committed anywhere.

**Current disposition:** approved as the first research path for outcomes/identity, subject to dataset-specific verification.

### DynastyProcess archived FantasyPros-derived data

**Role:** candidate historical projection / consensus / ranking source.

DynastyProcess maintains fantasy-football data in a public repository and has automated FantasyPros-related update workflows. Git commit history can potentially provide conservative availability timestamps for retained snapshots. However, the repository license and the rights governing upstream FantasyPros data are separate questions.

**Current disposition:** investigate for private historical research. Do not redistribute copied upstream tables or assume commercial rights.

### Razzball

**Role:** candidate independent projection source.

Razzball exposes projection products and dated projection pages, but historical completeness and applicable usage terms must be verified before the source enters the scored cohort.

**Current disposition:** investigate.

### FantasyPros direct

**Role:** candidate projection / consensus source and useful comparator.

FantasyPros is an aggregate and therefore may overlap with component sources. It cannot automatically be treated as an independent model vote. Historical API access and downstream use rights require explicit review.

**Current disposition:** requires access/terms review before acquisition.

## Batch execution plan

The first benchmark run should follow one path for every source:

1. acquire dated historical artifacts;
2. assign conservative `issued_at` / availability timestamps;
3. normalize player identity and target period;
4. convert records to canonical `HistoricalProjectionSnapshot` objects;
5. join against normalized realized outcomes;
6. split chronologically into training and held-out evaluation periods;
7. score every individual source by position and horizon;
8. score equal weighting;
9. learn challenger weights only on training history;
10. score the challenger on held-out history;
11. evaluate uncertainty calibration where the source provides uncertainty information;
12. report coverage, missingness, sample size, and source dependence alongside accuracy.

## Efficiency rule

Provider-specific work stops at the adapter boundary. Once a provider has been normalized, it must use the same benchmark machinery as every other provider. No one-off scoring notebooks, custom weighting logic, or provider-specific evaluation rules should be introduced unless the underlying data meaning truly requires it.

## Promotion rule

The first benchmark is a research study, not automatic production promotion. A challenger earns production authority only if it demonstrates repeatable held-out improvement over sensible baselines, has adequate sample support, behaves sensibly across important cohorts, and can be reproduced from governed inputs.

## What counts as success for the first run

The first run does not require a perfect historical archive. It succeeds if we can produce a defensible multi-source comparison with enough coverage to answer:

- which sources are strongest by position and horizon;
- whether equal weighting improves on individual sources;
- whether evidence-derived weighting improves on equal weighting out of sample;
- where the data is too thin to support differentiated weights;
- how much uncertainty and source disagreement should be carried forward;
- which missing sources are worth adding next.

That result is sufficient to establish a first production forecasting baseline while keeping the research pipeline open to better data later.
