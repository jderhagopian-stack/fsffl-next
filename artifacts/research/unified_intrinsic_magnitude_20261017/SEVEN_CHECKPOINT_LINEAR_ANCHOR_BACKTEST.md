# Seven-checkpoint anchor backtest — 2026-10-17

Read-only measurements from Supabase fsffl.derived_artifact Career checkpoint IDs 10308 (Oct 5), 10829 (Oct 6), 11741, 11795 (Oct 15), 11839 (Oct 16), and 12005, 12063 (Oct 17). Snapshots contain 334–335 players. These are **repeated nearby checkpoints, not independent seasons**; results do not establish long-run anchor stability.

|Checkpoint ID|Players|Max raw 3-Year|Max raw Career|3-Year clipped @750|Career clipped @2000|Career clipped @2100|Career clipped @2200|
|---|---:|---:|---:|---:|---:|---:|---:|
|12063|335|724.12|2062.30|0|1|0|0|
|12005|335|724.12|2062.30|0|1|0|0|
|11839|334|724.98|2065.49|0|1|0|0|
|11795|334|724.98|2065.49|0|1|0|0|
|11741|334|724.98|2065.49|0|1|0|0|
|10829|335|723.92|2062.37|0|1|0|0|
|10308|335|723.94|2062.64|0|1|0|0|

Raw 3-Year reconstructed as Y1 + 0.85 Y2 + 0.7225 Y3 from the exact same checkpoint as raw Career. SQL comparisons tested clipping at the fixed anchors. 2100 and 2200 avoid all observed Career clipping. **2100 is an observed-sample non-clipping candidate, not a guaranteed permanent ceiling; 2200 offers more headroom but compresses scores by ~4.5% versus 2100.**

## Gate

Retain linear as research lead and separately governed horizon anchors. Do not claim that the same 0–10,000 index represents identical economic units between horizons or Market. Before promotion, test longer-term forecast/state diversity, stability and changes to player pool; adopt explicit clipping/overflow policy and verify matching State fingerprint. No production wiring or merge.
