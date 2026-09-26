# Current Horizon Diagnostics — 2026 Shadow

Authority: research shadow only.

## Rank continuity and movement

| Diagnostic | Result |
| --- | ---: |
| H3 shadow vs production H3 Spearman | 0.9965 |
| H3 vs H5 rank Spearman | 0.9857 |
| H3 vs H8 rank Spearman | 0.9672 |
| Median absolute H3→H5 move | 7 |
| P90 absolute H3→H5 move | 19 |
| Players moving >=10 H3→H5 | 36.1% |
| Players moving >=20 H3→H5 | 9.3% |
| Median absolute H3→H8 move | 12 |
| P90 absolute H3→H8 move | 30 |
| Players moving >=10 H3→H8 | 59.4% |
| Players moving >=20 H3→H8 | 25.4% |

## Position share of top assets

| Horizon | Top cohort | QB | RB | WR | TE |
| --- | --- | ---: | ---: | ---: | ---: |
| H1 | Top 25 | 80% | 16% | 4% | 0% |
| H3 | Top 25 | 88% | 8% | 4% | 0% |
| H5 | Top 25 | 76% | 8% | 16% | 0% |
| H8 diagnostic | Top 25 | 72% | 12% | 16% | 0% |
| H3 | Top 50 | 52% | 32% | 16% | 0% |
| H5 | Top 50 | 50% | 26% | 24% | 0% |
| H8 diagnostic | Top 50 | 50% | 20% | 30% | 0% |
| H3 | Top 100 | 31% | 31% | 32% | 6% |
| H5 | Top 100 | 29% | 29% | 35% | 7% |
| H8 diagnostic | Top 100 | 29% | 28% | 35% | 8% |

## Age-band mean rank movement

| Position / band | H3→H5 | H3→H8 |
| --- | ---: | ---: |
| QB young | +21.3 | +32.7 |
| QB prime | +5.4 | +7.7 |
| QB aging | +0.6 | +0.7 |
| RB young | +0.9 | +4.6 |
| RB prime | -5.9 | -8.8 |
| RB aging | -12.6 | -21.2 |
| WR young (n=4) | +7.0 | +14.5 |
| WR prime | +3.9 | +6.1 |
| WR aging | -9.4 | -18.0 |
| TE young (n=4) | +7.0 | +11.0 |
| TE prime | +0.3 | +4.3 |
| TE aging | -8.3 | -15.3 |

Positive values mean the player moves toward rank 1 as the horizon extends.

## H5 forecast uncertainty floor

| Position | OOT floor (FP) | Floor / current mean expected Y5 |
| --- | ---: | ---: |
| QB | 101.1 | 1.96× |
| RB | 52.4 | 2.37× |
| WR | 35.4 | 1.27× |
| TE | 30.4 | 1.76× |

The high ratios mean H5 can contain useful ordinal/durability information while still being too uncertain for false point precision.

## Illustrative post-selection crossover examples

| Player | Pos | H3 rank | H5 rank | Delta |
| --- | --- | ---: | ---: | ---: |
| J.J. McCarthy | QB | 269 | 146 | +123 |
| Justin Fields | QB | 281 | 174 | +107 |
| Troy Franklin | WR | 231 | 155 | +76 |
| Elic Ayomanor | WR | 248 | 172 | +76 |
| Drake London | WR | 44 | 31 | +13 |
| Christian McCaffrey | RB | 30 | 40 | -10 |
| Derrick Henry | RB | 58 | 76 | -18 |
| Keenan Allen | WR | 204 | 226 | -22 |

These examples were inspected only after the model family was frozen and are not calibration targets.
