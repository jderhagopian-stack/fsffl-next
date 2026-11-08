# Intrinsic display scale review and next development — November 8, 2026

## User direction and verified repository

User confirms the repaired capabilities work, though very slowly, and asks to resume useful/consistent Intrinsic 0–10,000 translation. Main verified at `e0e045a44b4c5b19061922995b1a49d3347c91d2`, same current live #522 release. This is an audit/proposed next workstream, not authorization of a new live calibration, economic model or provider/plan change.

## Operational acceptance update

New State `f0aebd5971731782c6c56257d3d42b18d072bd4bdab9282e349577a137cfb28c`, final generation `4066eb145b116407312f46ac7e2a7e2ee51eeb3185df8b6cf65becf36c1b036a`, pointer saved **14:22:17.511013 UTC**, atomic phase finished **14:22:19.425883 UTC**. Career saved at **14:21:27.054669 UTC**, **367 estimates / no player coverage failures**. Pierce retains the explicit earned-YTD/no-additional-ROS assumption and accepted future models. Saved Career rooms are **12/12 complete for QB/RB/WR/TE**, including RB. User physically confirms operational recovery, including the previously missing columns. Do not extend this to broad coverage/scalability acceptance for untested leagues/waiver cohorts.

Core publication atomic save finished **14:13:24.989589 UTC**. Career-backed publication followed about **8m54s** later. Phase measurements: exact reference restore **2.897 s**; current inputs/P0 **11.913 s**; Foundation 4 historical fitting/materialization **194.967 s wall / 95.673 s CPU**; about **4m56s** remained between fitting completion and final publication, comprising later composition/persistence work without finer phase attribution. Do not call fitting the entire refresh or attribute all later time to one unmeasured stage.

Post-refresh read telemetry at **14:41:43 UTC** shows compatibility identity resolution **3.193 s**, RSS around 560–566 MB, process high-water **569,745,408 B (~543.35 MiB)**. Render 30-second charged-memory maximum **517,689,340 B (~493.71 MiB)** at 14:42; CPU reached **0.5** in the refresh interval. No server failure/restart event was returned for the checked period. Process RSS and charged memory differ; samples can miss peaks. Reliability improvement is physically confirmed; read/refresh latency and headroom remain open gates.

## Governing scale work recovered

Issue **#375**, “Product: distinguish 3-Year Intrinsic from Career Intrinsic”, requires separate governed horizon-specific 0–10,000 coordinates, Career primary for dynasty, raw economics preserved, no Market/age/display-index blend into Career, and no automatic economic subtraction between horizons. It is the relevant integration thread, not the separate Market-cardinal research/promotion.

`docs/value/fsffl-value-score-plan.md` explicitly distinguishes cardinal magnitude from percentile ordering. Its later Market promotion `docs/value/fsffl-cardinal-promotion-v1.md` is an already accepted **Market** coordinate, not permission to import market prices into Intrinsic or to re-run that research. Foundation 4's original career-tail directive preserves raw undiscounted annual Shapley sum plus tail; 3-Year retains its governed discounted Y1–Y3 coordinate. Do not silently harmonize those underlying economics merely to simplify display.

## Current code and consequences

- `product/value_lens_evidence.py:percentile_ranks` converts Intrinsic raw values into cross-player midrank percentiles, discarding raw gap magnitude.
- `product/value_presentation.py:build_value_presentation_coordinate` constructs 101 percentile knots from a median of provider-native Market distributions independently min/max normalized to 0–10,000.
- `product/league_value_lens_routes.py:with_career` applies that Market-shaped coordinate to the percentile of Career-owned discounted Y1–Y3 values. Thus 3-Year ordering comes from Intrinsic, while display spacing comes from Market shape. Its ranked cohort can change with covered subjects.
- `product/career_presentation.py:CareerPresentationCoordinate.index` maps the Current-owned active reference Career game to empirical midranks ×10,000, interpolating between anchors and clamping outside them. It avoids changing the ruler merely because a dynamic roster player is added, but anchor spacing reflects rank instead of raw economic gaps. It is an accepted ordinal display implementation, not a newly discovered raw-model defect.
- Other consumers include player intelligence, market lenses/discovery and roster cards. A replacement must have one authoritative versioned transform consumed across them; no per-screen rescaling.
- Position & Depth ranks/Strength Index consume raw room values. Their league-average=100 index is separate and must not be replaced with summed player display indexes.

Pure current-code demonstration: raw reference [1,2,100] maps to [0,5000,10000]. A raw gap of 1 and a raw gap of 98 get the same display gap. This was executed against current code; no model was fitted.

Actual saved final publication (Career values):

| Player | Raw Career | Career index |
| --- | ---: | ---: |
| Lamar Jackson | 1267.7280 | 9609.6096 |
| Omarion Hampton | 674.9080 | 8888.8889 |
| CeeDee Lamb | 553.9398 | 8228.2282 |

Raw adjacent gaps are **592.8200** and **120.9682**; display gaps are **720.7207** and **660.6607**. Current ranks are preserved, but those display differences cannot be read as relative economic spacing. This explains the user's consistency/usability concern without alleging the underlying valuations are incorrect. Raw quantities across the two horizons also have different temporal aggregation/discount semantics; equal nominal 0–10,000 ranges do not prove equal economic units.

## Proposed next deliverable (offline first)

Resume #375 with a bounded **Intrinsic coordinate v2 comparison**, using the current saved publication and accepted reference inputs, no Forecast/Simulation/Shapley/Career recomputation. Compare a fixed-anchor affine baseline and only justified monotone alternatives; show actual before/after players, raw gaps, zero/negative treatment, elite/mid/depth spacing, tie/outlier behavior and cross-publication/cohort stability. Do not choose an exponent, anchors or preferred player scores by intuition and silently deploy them.

Target one consistent Intrinsic scaling methodology with explicitly governed horizon/format reference calibration. Feed the raw horizon-specific Intrinsic quantities, preserve magnitude as far as the chosen bounded transform permits, and keep percentiles separately labeled. A fixed calibration/model version should not move merely because a fantasy roster or displayed query changes. Decide zero/negative and upper-range policies explicitly; finite bounded scales, gap preservation and unclipped outliers have tradeoffs. Broad Market stays independent. Matching index labels do not authorize cross-horizon subtraction or package addition.

Present the comparison and recommend a specific transform/anchor/version contract before changing live values. Then integrate the same fields across Franchise, Player Intelligence, Explore/Market and Trade-facing display; preserve raw Decision and room calculations and scale history/version metadata.

## Delivery order

1. **Next product deliverable:** the bounded coordinate-v2 audit/comparison above, resuming #375.
2. **Parallel release-quality obligation:** measure/shorten the post-fit composition/publication stages and eliminate repeated expensive compatibility resolution from ordinary reads. Reuse accepted computation at correct semantic scopes; preserve raw outputs and last-good publication. No provider/plan/worker migration implied. Do not treat surviving one refresh as comfortable headroom.
3. **After readable values and responsive reads:** validate the existing Explore → candidate → bilateral Trade workflow on a real publication; continue the independently governed historical/What-If/Owner/roadmap sequence with explicit evidence gates. Do not start new heavy capability breadth merely because current coverage is repaired.

This review makes no executable change or production mutation. Latest user statement is confirmation of operational recovery and a request to resume the scale discussion; no numerical candidate has yet been approved or deployed.
