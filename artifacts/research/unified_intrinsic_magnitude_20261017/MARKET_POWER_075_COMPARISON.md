# Independent magnitude ruler versus Market — measured diagnostic

On **331** October 17 published player rows with Market, raw 3-Year and raw Career, the following Pearson correlations were measured against published Market index. Raw horizons were extracted/reconstructed from retained Career checkpoint 12063, while Market index was joined from published all-player surface 12072 by canonical player ID. Same publication window, although a formally identical State fingerprint across checkpoint and surface is not independently established.

| Intrinsic coordinate | Market vs 3-Year | Market vs Career |
|---|---:|---:|
| Existing published Intrinsic indexes | 0.813 | 0.744 |
| Raw Intrinsic contribution | 0.841 | 0.750 |
| Test power-0.75 magnitude score | 0.834 | 0.775 |

Formula for test: `10000 * min(1, max(0, raw / anchor)) ** 0.75`, diagnostic anchor 750 for 3-Year, 2000 for Career. These anchor values were **not** historically validated.

**Interpretation:** Correlation can change under a monotonic display transformation and is not itself a basis for choosing curvature or anchors. In the absence of saturation and rounding, ordering cannot improve by applying a monotonic curve, so there is no legitimate claim of superior player rankings. Validate player-to-player value-gap fidelity, historical stability, and economic interpretation separately. The observed Market alignment is contextual; Market must not act as the economic authority for raw Intrinsic.

No raw valuation changes, production changes, merge or deploy are authorized.
