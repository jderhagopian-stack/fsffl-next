# FSFFL NEXT - State-specific magnitude identifiability / feasibility method

This stage does not fit a Forecast challenger. It analyzes the exact frozen D1 Y3 developmental-RB walk-forward coordinate.

Primary response diagnostic is log1p(realized target points) - log1p(frozen D1 mean for the realized positive future state), regressed descriptively on continuous source percentile. State-specific slopes use player x source-year Bayesian bootstrap uncertainty. Origin-level slopes require at least 5 realized-state rows and source-percentile span >=0.25. Leave-one-origin-out and leave-one-player-out influence are reported.

Partial-pooling feasibility is tested on the canonical economic ordering only: upper positive states = starter/premium/elite; lower positive states = depth/usable. This grouping is not based on p90 signs or a source-magnitude threshold. Evidence for pooling is the continuous lower-minus-upper magnitude-response contrast, its clustered uncertainty, origin recurrence, and leave-one-origin-out stability. Within-group state contrasts are also reported; intervals spanning zero argue against separate curves.

Residual-scale feasibility uses the absolute log1p residual versus continuous magnitude with the same clustered uncertainty. A future candidate is not required to parameterize magnitude-dependent scale unless this relationship is supported.

Effective support is reported as nominal N, unique players, Kish ESS by repeated-player counts, Kish ESS by origin counts, magnitude coverage, and repeated-player concentration.