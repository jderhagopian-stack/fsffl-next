# FSFFL NEXT — Current-Only FUMBLES_LOST Implementation Handoff

Updated: 2026-09-26 UTC  
Research state: **BLOCKED — EXTERNAL PROVIDER RIGHTS / LIVE CREDENTIALS**

## Outcome

Research has completed the implementation contract and identified the shortest technical two-independent-source path:

**JerryGM Projections API + LineupExperts Premium In-Season Projections**

This pair is materially stronger than the prior JerryGM + Fantasy Nerds path because both candidate inputs are direct projection-product paths and LineupExperts Premium now publicly proves an exact lost-fumble field (`FmblL`). Fantasy Nerds remains aggregate/consensus evidence and is not the preferred independent vote.

No unrelated offensive Forecast coordinate is rebased.

## What can be implemented once external gates clear

Implementation may add a 2026 current-only supplemental `FUMBLES_LOST` authority lane with these boundaries:

1. acquire current/ROS lost-fumble evidence from exactly two accepted independent sources;
2. keep source evidence labeled ROS/current with its real acquisition time;
3. normalize only this coordinate to a 17-game season-equivalent **current pace** for the existing current scoring/Simulation interface;
4. retain the immutable ordinary offense baseline unchanged;
5. overlay the supplemental metric only during current league scoring;
6. apply the specified non-zero empirical uncertainty floor plus provider disagreement;
7. make the supplement invisible to every cutoff before two-source acquisition;
8. permanently exclude it from 2026 preseason claims, annual preseason snapshots and historical PIT backfill.

Detailed contracts:
- `CERTIFICATION_LEDGER.md`
- `NORMALIZATION_UNCERTAINTY_CONTRACT.md`

## Source acceptance matrix

| Gate | JerryGM | LineupExperts Premium | Pair |
|---|---|---|---|
| exact lost-fumble semantics | PASS — `fumblesLost` | PASS — `FmblL` public Premium demo | PASS |
| current/ROS capability | PASS — `week=current&horizon=ros` | PASS — Premium In-Season supports ROS | PASS |
| schedule-period metadata | PASS in schema | PASS/needs paid ROS payload confirmation | CONDITIONAL |
| public current health evidence | PASS at schema/docs level; auth payload unavailable | PASS — current ROS population and schedule-aware GP visible | CONDITIONAL |
| canonical full-pool coverage | NOT VALIDATED without API key | NOT VALIDATED without paid API key | BLOCKED |
| provider independence | PASS — explicit own model | STRONG CANDIDATE; endpoint ownership needs written confirmation | BLOCKED |
| private-beta model-input rights | REVIEW_REQUIRED | REVIEW_REQUIRED | BLOCKED |
| non-zero uncertainty contract | PASS — retained empirical floor defined | PASS — same | PASS once source pair accepted |
| provenance contract | DEFINED | DEFINED | IMPLEMENTATION-READY |

## Exact external dependencies

Research cannot complete certification without all of the following:

### JerryGM
1. API key sufficient to capture the current full QB/RB/WR/TE pool.
2. Written confirmation that FSFFL may use the exact current `fumblesLost` API output as one input to a two-source current supplemental Forecast coordinate, while:
   - not using JerryGM output to train/calibrate FSFFL;
   - not redistributing the raw feed;
   - preserving required attribution/provenance;
   - exposing derived FSFFL current intelligence.

### LineupExperts
1. Premium In-Season Projections API entitlement/key with ROS access.
2. FSFFL private-beta application registered as a qualifying usage forum.
3. Written confirmation that:
   - `FmblL` Premium ROS values may be retained minimally and used as one input to the current supplemental coordinate;
   - derived FSFFL intelligence may be produced from them without raw-feed redistribution;
   - the Premium NFL projection endpoint values are LineupExperts-generated projection output rather than a third-party/aggregate projection feed, sufficient to count independently from JerryGM.

### After credentials/permission exist
Run one governed live acquisition and persist:
- exact endpoint/request identity without secrets;
- capture/effective/generated timestamps;
- source/model versions;
- content hashes where rights permit;
- raw row counts;
- canonical-match count;
- duplicate/ambiguous/unmatched counts;
- per-player two-source coverage;
- source `gamesRemaining/GamesPlayed` versus canonical schedule;
- zero/missing distinction;
- distribution of normalized current fumble rates;
- source disagreement distribution;
- final authority-valid-from timestamp.

Only that evidence can flip this certification from BLOCKED to accepted.

## Fallback if LineupExperts rights/ownership do not clear

**SportsDataIO** is the strongest clean direct-provider fallback:
- exact `FumblesLost` exists in player projection schemas;
- SportsDataIO offers current fantasy projections and advertises partial-season/ROS products;
- commercial licenses can explicitly authorize storage and model/analytics input.

Use it only under a license that covers the actual hosted FSFFL beta. Discovery Lab's personal-use license is not automatically sufficient for a hosted/private-beta application.

Do not fall back to Fantasy Nerds as the second independent vote without source decomposition proving independence.

## Implementation sequence after Research unblock

1. Add evidence-only source adapters for JerryGM and LineupExperts Premium.
2. Add `CurrentSupplementalForecastCoordinate` persistence/contract.
3. Implement schedule-aware source health and exact `FUMBLES_LOST` normalization.
4. Implement equal-weight season-equivalent current pace + non-zero uncertainty contract.
5. Add current-scoring overlay without mutating the ordinary raw Forecast bundle.
6. Add hard historical/preseason eligibility guards.
7. Run deterministic tests from the normalization contract.
8. Acquire a governed live two-source snapshot and validate full canonical coverage.
9. Rebuild current FSFFL Forecast.
10. Promote Simulation only if current player scoring is fully authoritative for the needed lineup universe.
11. Verify the preseason/raw baseline hashes remain unchanged and historical/preseason product surfaces cannot see the supplement.

## Operating-protocol check

Question: **Is there another authorized Research action available now that can clear the remaining source gates without external provider credentials or written usage/ownership confirmation?**

Answer: **No.**

Public Research has established the exact coordinate, current horizon path, target normalization, non-zero uncertainty rule, freshness contract, historical eligibility boundary, and shortest source pair. The remaining gates are external account/rights evidence and a paid live payload.

**BLOCKED — RESEARCH / EXTERNAL PROVIDER RIGHTS AND LIVE CREDENTIALS**
