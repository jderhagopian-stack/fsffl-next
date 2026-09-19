# Selected Forecast Internal Coordinate — Recovery Correction and Final Verification

Date: 2026-09-18

The earlier recovery manifest at df5e6440c8f48dad75bf8080e35f7515408f853b identified a valid player-keyed I1 probability artifact, but that artifact alone was not sufficient for the B2a Stage-C experiment: it contained only horizons 1/2 and did not cover every pre-holdout B2a coordinate. No S1/S2 fitting was performed from that incomplete coordinate.

The least-invasive recovery order then found an already-durable exact selected-Forecast artifact from PR #150:
- workflow run 35055361960
- artifact 10430792617 (live-forecast-horizon-selection)
- file live-forecast-horizon/selection/selection_rows.csv
- source code head c629371356836ae57c5df71fe9db2c83356ece8f
- architecture I1-direct-horizon
- global C=0.25
- source seasons 2014–2020
- horizons 1/2/3
- strict cutoff: training source + horizon < evaluation source season

This is the same direct completed-source I1 h=2/h=3 machinery frozen by PR #147 for Year 2 / Year 3. It is not an older substituted probability surface and required no refit or replay.

Exact join against the provisional B2a pre-holdout evaluation population:
- Y2: 2,376 / 2,376 joined
- Y3: 1,911 / 1,911 joined
- total: 4,287 / 4,287
- duplicate player/source/horizon keys: 0
- unexplained losses: 0
- folds: early 2014–16, mid 2017–18, validation 2019–20
- holdout 2021–22 excluded
- current board excluded

The selection artifact stores aggregate starter and premium probabilities under names that overwrite their individual state labels. The exact six-state vector is deterministically recovered from the artifact contract as:
- p_out = i1_out
- p_depth = i1_depth
- p_usable = i1_usable
- p_starter_state = i1_starter - i1_premium
- p_premium_state = i1_premium - i1_elite
- p_elite = i1_elite
This reconstruction has maximum probability-sum error 4.44e-16 and no negative state probability.

A 4,287-row reusable machine-readable subset aligned exactly to the B2a pre-holdout coordinates is persisted separately. Its SHA-256 is 9033076329100ac1934edeec503c8ebb229d5924504b2008bdde2a3a0053fb90.

No refit occurred. No S1/S2 outcome was inspected. Stage C may now resume from the previously frozen specification.
