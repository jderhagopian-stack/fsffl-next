# Developmental RB D1 distributional representation - final research conclusion

**D. STRUCTURAL CONCERN CONFIRMED BUT NO SAFE CHALLENGER**

The frozen D1/P0 machinery reproduces exactly. The unresolved developmental-RB high-source compression is therefore not an implementation defect.

The mechanism is now auditable. D1 predicts positive-state production in absolute future points. Source magnitude enters largely through a standardized log transform, and the learned RB response is strongly sub-unit: raising source points by 10% barely raises D1 conditional state means. At the same time, the shared ordered-state model includes `dpts = (source_points - prior1_points)/100` (clipped), whose RB threshold coefficients are negative. A current-season spike relative to prior history therefore pushes future active-state mass downward. Conditional production can stay flat or fall while the source-season denominator rises, mechanically producing a steep negative retention slope.

That behavior is not historically justified in the supported high-source developmental-RB Y3 tail. The frozen 2014-2020 anchor remains 25 active observations above 225.5 source points with realized median retention 0.698 versus D1 conditional-active 0.520 and mean retention bias about -0.126.

No existing alternative solves it. D0 remains similarly compressed. One minimal general challenger, D1R, was preregistered before fitting: it keeps state probabilities and every D1 feature/model choice fixed but predicts log retention/change rather than raw future-point level. D1R failed the frozen pre-holdout promotion gates. Its pooled Y3 CRPS improvement was uncertain and, critically, the high-source bias worsened instead of improving. Y2 also failed because the mid block worsened on CRPS and pooled uncertainty crossed zero.

Only after that failure was persisted, the locked 2021-2022 replication was evaluated once. It did not rescue D1R. Developmental-RB Y3 CRPS gain was +0.068 with a 95% interval spanning zero, and among the three locked high-source active cases realized median retention was 0.728 versus 0.499 for D1 and 0.482 for D1R. Collapse/state probabilities were identical by construction throughout.

Therefore the structural concern is confirmed, but no safe challenger earns research authority. P0/D1 remains the production control. The previously earned Forecast-wide prospective changes remain research-only: Y3 developmental QB D0->D1, Y3 established RB D0->D1, WR/TE unchanged, and proper distributional scoring added to future Forecast candidate selection with MAE as guardrail. No implementation, PR #147 modification, merge, or deployment is authorized here.