# Fixed versus season-frozen top-player linear ruler — diagnostic

Seven retained nearby October 2026 Career snapshots: 10308, 10829, 11741, 11795, 11839, 12005, 12063. They are highly correlated checkpoints, **not different NFL seasons**.

## Two approaches

- Fixed: 3-Year reference 750, Career reference 2200.
- Top-player: select the maximum raw contribution separately per horizon from an approved **full, valid, league-specific reference population at season start**, freeze that anchor for the season, and cap midseason exceedances at 10,000. Re-evaluation in offseason would change unchanged players' numbers.

## Observed reference changes

3-Year max ranges 723.92–724.98 (0.146% span); Career 2062.30–2065.49 (0.155% span). Tiny variation across these checkpoints says little about movement across years, exceptional breakouts, different rules, or changed reference cohorts.

## October 17 player scores

|Player|3Y fixed 750|3Y top 724.12|Career fixed 2200|Career top 2062.30|
|---|---:|---:|---:|---:|
|Jordan Love|6318|6543|5914|6309|
|Cam Ward|5336|5526|6548|6985|
|Derrick Henry|4470|4630|1772|1891|
|Brian Thomas|2930|3035|2241|2390|
|Riley Leonard|417|432|1680|1792|
|Stefon Diggs|2082|2157|841|897|

## Critical decision tests

1. Both approaches preserve raw ratios unless capped. Top-player makes highest observed player 10000 each calibration; fixed can reserve headroom for exceptional future players.
2. A per-season highest-player anchor depends on the chosen player universe and could shift on league-rule changes, roster scope, projection model revisions, or a different talent pool. Define reference population explicitly.
3. If top player disappears or peaks/declines, annual reanchoring changes scores for otherwise unchanged players. Quantify this on independent historical seasons before choosing.
4. Top-player normalization **does not create cross-league economic equivalence**; 8000 is 80% of that league/horizon's peak, not globally comparable value.
5. Midseason exceeding the frozen anchor clips all additional display value. We should separately show raw contribution and an explicit overflow indicator.
6. An alternative worth testing is a multi-year elite reference ceiling or a high historic benchmark with governed change control, rather than current-year top or arbitrarily padded maxima.

**Evidence limit:** no validation yet on multiple distinct seasons or league configurations. No basis to claim a winner. No production release authorized.
