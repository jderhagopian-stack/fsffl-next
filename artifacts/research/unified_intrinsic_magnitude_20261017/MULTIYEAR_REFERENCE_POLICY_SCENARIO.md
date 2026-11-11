# Multi-year elite-reference comparison — scenario test

**Status:** research only. True historical comparable Career Shapley estimates spanning distinct seasons were **not** available in the retained artifact store (Career contracts date from October 2026). This study tests **policy behavior** under illustrative distinct-year elite raw magnitudes, not realized player forecasts or reconstructed NFL greats.

Same hypothetical player's raw Career value remains **1100** in all years. Hypothetical top Career values by year: 2062.30, 2550, 1850, 2400, 2062.30.

|Year|Hypothetical season peak|Annual top-player anchored score|Fixed 2200 score|Rolling 3-year peak score|Rolling reference|
|---|---:|---:|---:|---:|---:|
|1|2062.3|5334|5000|5334|2062.3|
|2|2550|4314|5000|4314|2550|
|3|1850|5946|5000|4314|2550|
|4|2400|4583|5000|4314|2550|
|5|2062.3|5334|5000|4583|2400|

**Policy evaluation:** Annual peak recalibrates all scores when the best player changes. Fixed 2200 keeps an unchanged player's score constant but clips hypothetical superelite peaks over 2200. Rolling 3-year peak is resistant to brief declines in top-player value and smooths recalibration, yet it also clips a new peak until reviewed and eventually changes scores when exceptional seasons leave the window. A *historical elite high-water mark with nondecreasing versioned anchor* avoids score increases following decline but still changes scores on exceptional new peaks. Every policy needs an overflow rule.

Observed reality: October 2026 Career reference checkpoint 12121 had 335 players and max 2062.30; expanded Career run 12122 had 361 players and max 2062.30. That is evidence of stability under that particular 26-player cohort expansion, not different seasons or formats.

**Recommendation for further testing:** Do not select a winner from hypothetical peaks. Keep linear as the leading curve. Test frozen anchor against multi-season held-out, league-rule-normalized Shapley estimates and avoid automatic season-reset solely due to rank changes. No production change.
