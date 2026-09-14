# Latest Intrinsic Result — D2 Career-State Validation

## Decision

**KEEP A. Do not promote D2. Do not merge PR #138 yet.**

D2 successfully proves the core concept we were testing: future dynasty option value can come from explicit probabilities of entering valuable football states rather than from generic Forecast variance. It also materially fixes the first D implementation's within-state compression problem.

However, the underlying career-state probabilities/taxonomy are not calibrated well enough to support D2 as the production Intrinsic primitive. The remaining defect belongs in **Forecast career-state calibration**, especially RB/WR/TE. Do not invent another Value transformation.

## Exact validated state

- main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- D2 chronological research head: `0952aff12e9743f6bf1e584c9af339c8b0d5f87c`
- final validated PR head before management-artifact-only commits: `1bb4d40c50cd5048d038e168a4ebc2cf8889a100`
- PR #138: open, unmerged, mergeable
- PR #137: still superseded and unmerged
- unresolved review threads: 0

## What D2 is

D2 values the expected neutral-format franchise contribution across explicit future career states (`out`, `depth`, `usable`, `starter`, `premium`, `elite`). Generic Forecast standard deviation cannot move probability mass into a better state. Within a state, D2 uses the bounded smooth neutral contribution of the state-conditioned production distribution, while current-season contribution remains player-specific.

## Chronological result

On 6,758 holdouts across 12 chronological folds, using D2's smooth realized neutral-contribution target:

| Candidate | MAE |
|---|---:|
| **A** | **23.26** |
| B | 28.31 |
| C | 29.11 |
| first D, aligned to D2 target | 31.68 |
| **D2** | **34.87** |

D2 beat A in **0/12 folds**. It was worse than A at QB, RB, WR and TE, and worse for young, developmental, prime, aging and fringe players. It improved only the elite-tail MAE (98.9 vs A 113.3).

The most important developmental results were poor: developmental MAE **35.4 vs A 7.6**, young **53.6 vs 37.4**, fringe **19.8 vs 6.1**.

## Transition calibration

The transition probabilities are unchanged from first-generation D and remain the core blocker:

- upward transition: **29.1% predicted vs 37.3% realized**
- downward transition: **33.7% predicted vs 27.3% realized**
- multiclass Brier: **0.1215** on 3,997 state outcomes

D2 therefore underestimates real development and overestimates role loss. Changing the Value contribution function cannot repair this.

## Synthetic gate

D2 **passes the conceptual synthetic gate**:

- stable starting QB: **11.46**
- high-variance backup with weak upward path: **1.43**
- developmental QB with credible starter path: **10.81**
- WR with strong upward path: **8.05**
- similar WR with weak upward path: **1.44**
- elite young TE: **15.69**
- fringe TE: **0.25**

This confirms that D2 does **not** recreate C's generic-variance-as-free-upside pathology. Credible option value comes from explicit state probability.

## Current-player sanity

D2 materially reduces within-state compression. First-generation D, for example, gave Kyle Pitts and Trey McBride the same value (~6.54); D2 separates McBride **53.5**, Bowers **32.8**, Pitts **21.9** using player-specific current contribution plus bounded future states.

But the state model still produces important sanity failures. Nearly the whole target set is classified `elite`. Bijan **217.3 > Darnold 40.3** and the QB ordering is sensible, but Judkins **120.5** narrowly remains above JSN **120.1**, KC Concepcion **36.3 > Brock Bowers 32.8**, and McBride **53.5 > Bowers 32.8**. Those are state-model evidence problems, not a reason to add another Value curve.

Runtime is commercially trivial once state tables are cached: ~**0.046 seconds for 334 players** in the research sanity run.

## Final gates

- CI on `1bb4d40...`: **success — 1,195 passed, 2 non-blocking deprecation warnings**
- Fundamental Intrinsic Calibration on `1bb4d40...`: **success**
- D2 chronological workflow: **success**
- D2 current/synthetic sanity workflow: **success**
- leakage: no Broad Market, League Market, actual trades, owner behavior, team roster, specific replacement, or Team Utility inputs

## Next exact action

Keep **A** as the current Intrinsic primitive. Do not build D3 or another Value transformation. Improve the **Forecast-owned career-state taxonomy and transition calibration**, particularly RB/WR/TE upward-development and role-loss probabilities, then rerun this exact frozen D2 experiment. TE-premium scoring propagation remains a separate upstream integration repair.

**PR #138 remains unmerged pending management approval and the previously identified TE-premium integration repair.**
