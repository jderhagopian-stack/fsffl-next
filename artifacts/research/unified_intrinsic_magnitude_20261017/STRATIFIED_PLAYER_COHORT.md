# Stratified calibration player cohort — 2026-10-17

**Research only, read-only.** Source Career reference artifact 12005, matched Shapley 3-Year artifact 11748; 335/335 canonical-ID overlaps. Reference artifacts do **not** have identical State/cutoff; this is a candidate selection cohort, not exact-State acceptance. Do not apply these diagnostic scores to production.

## Reproducible selection

- Four positions: QB, RB, WR, TE.
- Three age stages from retained terminal features: young <25; prime 25 to <30; veteran >=30. Ages are inferred from retained model features, not independently verified roster DOB.
- Career raw-value tertiles **within position** (NTILE(3) ordered by raw Career).
- Within each nonempty position × age-stage × tertile cell select one player closest to its cell median raw Career, stable-tie by canonical ID.
- This produces **35 selected IDs**: 9 QB, 9 RB, 9 TE, 8 WR. Veteran/upper-tertile WR cell is empty; do not fabricate a replacement or redefine cohort silently.
- A small cell (e.g. some veteran RBs) may have only one qualified candidate. Selection is deliberately stratified and **not population-representative**; use full 335 for population-level distributions.
- Use additional outlier-focused cases and actual rostered/waiver players only after canonical State resolution; case inclusion can be additive and must not replace the stratified base cohort.

## Canonical player IDs, selected cells

|Position|Age stage|Low raw Career|Middle raw Career|High raw Career|
|---|---|---|---|---|
|QB|young|13425|12470|12522|
|QB|prime|7083|8161|6804|
|QB|veteran|2306|3257|3163|
|RB|young|13288|13305|13287|
|RB|prime|6039|8136|8150|
|RB|veteran|4137|4199|3198|
|WR|young|13329|13293|11631|
|WR|prime|7090|5045|10229|
|WR|veteran|4039|2449|— no qualifying record|
|TE|young|10231|11597|10859|
|TE|prime|10871|5844|7600|
|TE|veteran|5008|3214|4217|

IDs in table are Sleeper canonical suffixes (prefix `sleeper:player:`).

## Sampled cases highlighting critical review categories

|Player ID|Position/stage|Raw 3-Year|Raw Career|Y4–Y7|Y8+ tail|Demo 3-Year|Demo Career|
|---|---|---:|---:|---:|---:|---:|---:|
|12470|QB / young / middle|31.3|369.6|218.7|111.1|2042|4299|
|12522|QB / young / high|400.2|1440.4|287.0|690.0|7304|8487|
|8161|QB / prime / middle|350.6|743.8|68.4|277.4|6837|6098|
|3163|QB / veteran / high|521.3|1224.3|460.8|160.7|8337|7824|
|13287|RB / young / high|381.9|561.8|8.1|112.1|7136|5300|
|3198|RB / veteran / high|335.3|389.9|20.6|2.8|6686|4415|
|11631|WR / young / high|219.7|493.0|152.7|81.9|5413|4965|
|2449|WR / veteran / middle|156.2|185.0|4.7|6.7|4563|3041|
|10859|TE / young / high|196.2|377.3|93.5|58.6|5115|4343|
|4217|TE / veteran / high|161.4|249.8|64.4|4.4|4639|3534|

Demo only: fixed-anchor sqrt 3-Year anchor 750, Career anchor 2000; neither anchor is validated, exact existing published scores are not yet matched.

## Research gates

1. Resolve canonical names, precise career stage/experience and current exact-State status (rostered, free agent, unsupported); do not guess names from Sleeper numeric IDs.
2. Produce all 35 rows on a *single same-cutoff State* with **raw 3-Year Shapley, raw Career, Y1–Y3, Y4–Y7, terminal, existing published 3-Year/Career, rank-percentile, linear, sqrt, selected additional candidates** and missing-reason codes.
3. Add intentional extremes: top raw per position, highest terminal share, extreme 3-Year–Career disagreement, older starter, low-value high-percentile case, player newly added to population, rookie and unsupported row.
4. Test each position against genuine superflex lineup economics, no positional normalization to force elite frequencies.
5. Holdout and historical reference selection remain open. No production UI wiring until both horizon anchors are validated and Management approves their simultaneous release.

## Current findings

- Raw Career is QB-heavy at the high end; this is present before any display mapping.
- Young QB 12470 has 31.3 raw 3-Year vs 369.6 Career, a major long-horizon concentration requiring player/model review.
- **No claim** has been made that these provisional index scores are economically correct or that the retained cohorts are exact-State aligned.
