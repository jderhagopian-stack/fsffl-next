# Historical multi-season Career replay: evidence gate (2026-10-17)

A recovered 1999–2025 player-season panel was audited across **five independent starting seasons**: 2003, 2006, 2009, 2012 and 2015. Cohorts consist of the actual historical QB/RB/WR/TE player universe at each starting season, not a cherry-picked list of stars. Historical future observations are *hindsight outcomes* and are never relabeled as point-in-time forecasts.

|Start year|QB|RB|WR|TE|All|
|---|---:|---:|---:|---:|---:|
|2003|78|185|192|104|559|
|2006|75|180|194|105|554|
|2009|77|173|191|105|546|
|2012|70|174|216|114|574|
|2015|74|173|212|119|578|

**10,877 observed rows** for the five start-year cohorts over their next eight seasons (deduplicated by player ID and season). An athlete absent in Y8 is **not** automatically a modeling failure; it can represent retirement, injury, or lack of roster opportunity. A missing record is not a governed zero without further verification.

## Non-negotiable semantic boundary

The current raw Career contract is an additive Shapley model requiring (1) current Y1–Y3 marginal contributions evaluated in a league-format-specific full eligible universe, (2) modeled Y4–Y7 marginal contributions, and (3) a separately modeled Y8+ terminal. Replaying NFL observed fantasy points directly **does not** reconstruct this career contract.

The existing panel provides *historical outcomes* but does not supply contemporaneous forecast vintages and full governed league-specific rules for each season; therefore **no historical raw Career Shapley numbers or historical cap recommendation have been calculated or approved**. Future observations must not leak into contemporaneous forecasts. Hindsight oracle is a separate diagnostic, not production forecast evidence.

## Next executable gate

Obtain or reconstruct valid historical scoring/lineup fixtures, obtain point-in-time forecast input vintages, execute the actual frozen Shapley module for full cohorts and yearly horizons, and handle career tail authority using the governed method. Record each year/model version, compare held-out seasons across formats, and then compare fixed/annual-peak/multiyear-elite linear anchors. Never use a raw fantasy point proxy as a native Career score.

**Research-only; no merge or production wiring.** Input coverage artifacts were generated locally and can accompany execution once the legal provenance of recovered historical data is cleared.
