# Position and horizon calibration audit — 2026-10-17

**Evidence:** Supabase retained artifacts Career checkpoint `12005` and 3-Year Shapley `11748`; matched by canonical player ID, 335/335. This is a diagnostic cross-snapshot comparison, **not** exact-State recalculation, historical holdout, or production approval.

The demonstration formula is `10_000 * sqrt(min(1, max(0, raw / anchor)))`, with temporary anchors 750 (3-Year) and 2,000 (Career). Do not ship those numbers as permanent anchors. The scoring function never calls Market, ranks, or positional normalization.

| Position | Matched n | Raw Career mean | Demo 3-Year score mean | Demo Career score mean | Demo Career >=8000 | Demo 3-Year >=8000 |
|---|---:|---:|---:|---:|---:|---:|
| QB | 61 | 702.8 | 4937 | 5221 | 13 | 15 |
| RB | 89 | 266.2 | 4404 | 3320 | 0 | 2 |
| WR | 121 | 273.0 | 4170 | 3450 | 0 | 0 |
| TE | 64 | 196.6 | 3419 | 2916 | 0 | 0 |

### Interpretation

- QB concentration is **real in the retained raw Career inputs**; it is not newly introduced by the common monotonic display mapping.
- Relative-to-3-Year Career score effects may legitimately reflect position longevity and superflex lineup demand, but may also expose tail-model authority limits. Inspect tail Y8+ contribution by position and actual representative player cases; do not force equal percentages of high scores for each position.
- Converting each position's percentiles separately would eliminate interposition magnitude information and is **not** acceptable as the primary Intrinsic display scale.
- A concave conversion offers improved low/midrange readability over linear but does **not** preserve original ratios. Report raw differences and raw ratios separately; display scores are not additive.
- Ranking changes as low-value candidates join a percentile reference do not change fixed-anchor score for existing unchanged raw values; test this algebraically and empirically against changing reference populations.

### Open criteria

1. Historical validation population sufficient to select stable anchors (rather than observed maximum or conveniently rounded constants).
2. Same-cutoff exact-State comparison between raw 3-Year Shapley, Career, existing displayed indices, and both shadow candidates.
3. Player-level identities, including C.J. Stroud, Tua Tagovailoa, Shedeur Sanders, Justin Fields, Jalen Milroe **only when** authoritative State supports them; show unsupported explicitly.
4. Future cutoff holdout; ratio/gap preservation; upper-end saturation; alternate league configurations; position concentration; tail authority.
5. Focused CI + full-suite where required, no changes to core model, separate management decision approving both horizon displays together.

**Gate status: NO-GO for live calibration release.** This report only advances diagnostic evidence, not release authorization.
