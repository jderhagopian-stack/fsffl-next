# NEXT-2 Historical Projection Source Research

## Purpose

Identify sources that can support honest point-in-time historical forecast evaluation without making FSFFL NEXT dependent on one provider or on data we cannot lawfully retain or redistribute.

## Screening criteria

Every candidate is evaluated on point-in-time recoverability, QB/RB/WR/TE and horizon coverage, stat granularity, player/period matchability, timestamp quality, licensing/redistribution, replaceability, and commercial-path safety.

## Candidate source notes

### nflverse / nflreadpy

**Primary role:** realized outcomes and player identity backbone.

This remains the strongest open-data path for scoring historical forecasts and normalizing player identifiers. Dataset-specific rights still need to be checked before retained or redistributed data is committed.

Status: **APPROVED RESEARCH PATH for outcomes/identity, subject to dataset-specific verification.**

### DynastyProcess / FantasyPros ECR archive

The `load_ff_rankings(type="all")` path maps to DynastyProcess `db_fpecr`. Current nflreadr documentation describes it as a full archive of FantasyPros expert-consensus rankings, with weekly archives available since 2019. The published data dictionary includes `scrape_date`, ECR, ranking standard deviation, best/worst expert rank, player identifiers, position, and related ranking metadata.

This is important point-in-time evidence, but it is **ranking/ECR evidence, not raw statistical projection evidence**. It should therefore be used as a ranking comparator or separate market/consensus signal and must not be forced into the raw-stat forecast schema or counted as an independent projection model vote.

Status: **VERIFIED HISTORICAL RANKING/ECR CANDIDATE; not a raw projection source.**

Upstream FantasyPros data rights remain separate from the DynastyProcess repository license, so redistribution/commercial use still require review.

### Razzball

Useful candidate for actual preseason, weekly, and rest-of-season projection research because its public products expose underlying football-stat projections rather than only ranks. Historical completeness, archive timestamp quality, and terms still need verification before it enters the scored cohort.

Status: **PRIORITY RAW-PROJECTION INVESTIGATION.**

### FantasyPros direct

Useful candidate for current or licensed projection access and as an aggregate comparator. Historical/bulk access and downstream rights should be treated as provider-license questions. Because FantasyPros aggregates other sources, it cannot automatically be treated as statistically independent from component providers.

Status: **REQUIRES ACCESS / TERMS REVIEW.**

## Research architecture decision

Ranking evidence and statistical projection evidence remain distinct.

A historical ECR/ranking archive can be highly useful for ranking accuracy, consensus comparison, and later market/behavioral research, but it cannot be converted into invented passing/rushing/receiving projections or treated as a direct substitute for a provider that actually forecast those statistics.

The raw forecast benchmark therefore continues to require multiple genuine projection sources.

## Data-acquisition design

Every genuine projection source uses the same path:

**Discover source → verify timestamp semantics → verify terms/license → acquire dated artifact → preserve source metadata → normalize behind adapter → match to actual outcomes → split chronologically → evaluate through the common benchmark.**

A current webpage is never proof of what was knowable historically. Historical inputs require a dated artifact, provider-supported historical query, archived snapshot, or another defensible availability record.

## Storage policy

The public repository may contain adapters, schemas, evaluation code, synthetic fixtures, source-governance metadata, and reproducible instructions where permitted. Copied provider datasets do not automatically belong in the public repository; retained research data must follow source-specific rights.

## Statistical safeguards

Historical weighting must account for correlated sources, missing-player bias, survivorship bias, position/horizon sample size, preseason versus in-season timing, scoring effects, repeated player-season observations, source update timing, and uncertainty in estimated source skill.

No provider receives permanent weight because of reputation.

## Immediate execution order

1. Keep nflverse as the realized-outcome and identity backbone.
2. Treat DynastyProcess/FantasyPros `db_fpecr` as a separate historical ranking/ECR comparator, not a raw projection source.
3. Prioritize acquisition of several genuine raw projection sources, beginning with defensible Razzball archives and FantasyPros direct/licensed historical access where available.
4. Search for additional historical stat-projection archives in parallel rather than serially.
5. As soon as 3-5 genuine sources have sufficient overlapping point-in-time coverage, run them through the existing held-out multi-source benchmark together.
6. Add additional providers later through adapters without redesigning the benchmark.

The objective remains a broad first benchmark quickly, followed by evidence-driven refinement rather than an open-ended provider-by-provider research project.
