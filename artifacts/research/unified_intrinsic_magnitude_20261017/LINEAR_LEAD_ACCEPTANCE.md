# Linear magnitude ruler — lead calibration hypothesis (2026-10-17)

**Research-only.** Linear is the current leading hypothesis, not an approved production switch. Its core economic virtue: for positive unsaturated raw Shapley contributions, score ratios exactly preserve raw contribution ratios. Native Market remains independent and display-index differences are not trade surplus.

## Measured current cohort (checkpoint 12063)
335 concurrently reconstructed 3-Year and Career raw values. Historical/provisional reference 750 for 3-Year and 2000 for Career:

|Metric|3-Year raw|Career raw|
|---|---:|---:|
|Maximum|724.12|2062.30|
|95th percentile|479.11|1138.63|
|99th percentile|568.44|1743.65|
|Count at or above provisional anchor|0 / 335|1 / 335|

With provisional anchors, the linear Career ruler clips **one** player, destroying proportionality above 2,000. The 3-Year ruler clips none. The observed maximum suggests these anchors are plausible starting points, **not** historically established stable ceilings. A fixed reference must be selected from multi-snapshot evidence with forward holdouts, not the current maximum or current cohort quantile.

## Release gates

1. Preserve strictly proportional scores for uncapped nonnegative raw values. Zero maps to zero; negative raw shows as zero only in the display, while native signed raw remains authoritative. Missing values remain missing.
2. Evaluate anchor candidates on **multiple historical States**: percentage clipped, scale drift, real intra-tier gaps, and effects on 35 specified sample players; do not re-fit on each player population or season.
3. Establish an explicit overflow policy: clipping at 10,000 cannot be hidden as if elite values remain proportional. Document exceptional-case raw value alongside score, or revise a reference anchor through an explicitly versioned governance review.
4. Keep distinct 3-Year and Career raw units and reference anchors. A 3-Year index point **does not** automatically equal a Career index point or a Market index point.
5. Compare all three published lenses only as independent signals until there is a separately validated economic Market bridge. Future Team Utility consumes native marginal contributions, not scores.
6. Verify source checkpoint and published presentation share a formal State/cutoff fingerprint before claiming release-acceptance parity. Retained raw equations independently matched 335 older 3-Year contracts numerically, but checkpoint 12063 lacks State key.
7. No production wiring, merge, or deployment without acceptance.

The full 35-player linear versus nonlinear comparison is in `LINEAR_VS_POWER_075_35_PLAYER_RESULTS.md`.
