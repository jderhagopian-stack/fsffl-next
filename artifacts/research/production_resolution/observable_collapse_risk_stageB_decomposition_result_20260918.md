# Observable Collapse-Risk Stage B — Roster Signal Decomposition Result

Date: 2026-09-18
Workflow run 35405053495; artifact 10571772765.
Source: frozen Phase-2 artifact 10486530017 + source-season-only nflverse weekly rosters 2014–2020. No model fitting. Stage C remains closed.

## Main findings

1. The relationship is not a clean 25% cliff.
Across non-active-share bins, role-loss generally rises as source-season non-active burden becomes substantial, but it is noisy/non-monotonic at the extreme. Examples:
Y2 role-loss rates: 0–5% 20.4%, 5–10% 18.8%, 10–20% 21.4%, 20–30% 33.3%, 30–40% 26.0%, 40–50% 41.2%, 50–75% 36.2%, 75–100% 28.4%.
Y3: 22.5%,17.7%,20.5%,33.3%,42.5%,45.5%,31.6%,30.6%.
Therefore 25% must not be treated as a production threshold.

2. Duration and recurrence are more reproducibly informative than isolated absence.
Maximum non-active run:
Y2 role-loss: 0 weeks 20.4%; 1 week 17.7%; 2 weeks 23.6%; 3–4 weeks 29.7%; 5+ weeks 32.0%.
Y3: 22.5%;17.0%;28.3%;27.8%;35.4%.
Pattern:
Y2 none 20.4%, isolated single 17.7%, single stretch 27.0%, repeated stretches 33.3%.
Y3 none 22.5%, isolated single 17.5%, single stretch 28.4%, repeated stretches 36.1%.
This strongly argues against treating a one-week absence as the same structural warning as repeated/prolonged unavailability.

3. Recency matters, but is not a simple monotone severity scale.
Last-four-week non-active burden of 75–100% has Y2 role-loss 29.5% and Y3 34.0%, versus 21.8%/23.3% for zero late absence. Intermediate bins are noisy. Late-deterioration pattern is clearer:
Y1 24.8% vs 19.9%; Y2 31.0% vs 21.1%; Y3 32.1% vs 23.0%.

4. A naive “recovered to active” flag is NOT protective enough to be eligible.
Among all rows, the recovered flag has Y1 role-loss 20.3% vs 20.6%, Y2 29.7% vs 21.2%, Y3 28.0% vs 23.4%. Among high-burden rows it can be worse. Although recovered players have higher future target-presence, recovery-to-active alone does not erase long-horizon role-loss risk. Therefore roster ACT status is not equivalent to recovered full football role.

5. Position heterogeneity is material.
At >=25% burden versus below:
Y2 QB 46.2% vs22.7%; RB31.1 vs22.9; WR35.9 vs17.3; TE19.6 vs21.7.
Y3 QB28.6 vs26.9; RB28.1 vs23.7; WR45.6 vs17.4; TE37.8 vs24.7.
The signal is not safely blanket across positions.

6. Age does not explain the signal away.
Within position/source-season age quartiles, >=25% burden is higher in most horizon/quartile cells. Y2 rates by Q1–Q4: 34.3/33.3/27.3/32.0% warning versus 19.7/24.9/18.3/19.4% controls. Y3: 32.2/39.1/47.2/25.8% versus21.7/22.5/22.5/21.3%.

7. Chronology is not uniformly stable.
The >=25% signal is strong in many source seasons, especially 2014, 2016, 2019, 2020, but weak/reversed in some cells (notably 2017–2018 at shorter horizons and 2015 Y2). This prevents declaring the raw burden signal universally durable.

## Stage-B interpretation
The reproducible roster evidence supports a more specific source-time warning family: prolonged and/or repeated non-active stretches, especially when deterioration is late, carry future role-loss information. Isolated one-week absence does not. However, raw roster status cannot reproducibly distinguish temporary injury/availability from durable role/security deterioration, and the naive end-of-season active-recovery flag is insufficient. Position and chronology heterogeneity remain material.

Therefore Stage C is NOT opened. Before eligibility, the causal reconstruction must determine whether the high-leverage cases' repeated/prolonged/late patterns correspond to source-time durable structural facts versus temporary availability, and controls must verify any such causal category.

No S1/S2 fitting; no holdout/current-board selection; no main/PR147/production/Shapley changes.
