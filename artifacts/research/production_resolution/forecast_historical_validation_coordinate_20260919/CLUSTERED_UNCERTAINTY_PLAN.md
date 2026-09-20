# Clustered uncertainty plan

For every future Forecast candidate comparison, calculate paired row-level score differences against the frozen control.

Primary interval:
1. Two-way cluster bootstrap over source_season and player_id, preserving all rows belonging to sampled clusters.
2. 2,000 deterministic bootstrap draws with a preregistered seed.
3. Report mean paired gain and percentile 95% interval.

Temporal sensitivity:
- Resample contiguous source-year blocks with block length equal to horizon code (2 for Y2, 3 for Y3).
- Report origin-level sign share, median gain, worst-origin gain, and leave-one-origin-out pooled gains.

Do not use an IID row bootstrap as the sole uncertainty estimate. For cross-horizon summaries, keep horizon-specific inference separate and treat any combined view as descriptive.