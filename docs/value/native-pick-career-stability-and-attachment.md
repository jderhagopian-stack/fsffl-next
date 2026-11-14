# Native pick Career sensitivity and stored-source attachment

The latest checks support continuing research, not releasing the current Career
pick estimates. They identify sensitivity to selection sources as well as draft
classes. They do **not** demonstrate a defect in the accepted player Intrinsic,
Forecast, Shapley, scoring or Career models.

## What was compared

The existing research artifacts contain a 2018 multi-author Superflex mock's first
24 slots, a 2019 multi-author 2QB/Superflex mock's first 24, and the first 36 slots
from 53 qualified actual 2019 Superflex drafts. The mature samples reuse the same
connected-scoring annual games and accepted terminal model. No annual games or
production refreshes were rerun.

`scripts/audit_native_pick_career_stability.py` compares model reference centers
without creating a pooled value, fitting a correction or promoting a model.
Missing ranks remain missing. Source identities, economic coordinates and finite
model-authority envelopes are checked. Multiple sources for the same class do
not increase the independent-class count.

The descriptive gap is `2 × |a − b| / (|a| + |b|)`, zero when both centers are zero.
It is not forecast error, predictive uncertainty or a confidence interval.

| Comparison | Common slots | Independent classes | Median symmetric gap |
|---|---:|---:|---:|
| 2019 mock versus actual 2019 drafts | 24 | 1 | 45.7% |
| 2018 mock versus actual 2019 drafts | 24 | 2 | 62.4% |
| 2018 mock versus 2019 mock | 24 | 2 | 110.0% |

The second and third comparisons change both class and selection source. They
cannot isolate a class effect. The first comparison shows substantial source
sensitivity without changing the class. A multi-author mock is not expert
consensus: different participants selecting individual players is different from
aggregating independent rankings of every player.

A delete-one-draft check within the 53 actual 2019 records also leaves the class
unchanged. Across slots, the median maximum change in a slot center is 5.2%; the
largest is 21.6%. These are descriptive influence checks, not independent-sample
confidence intervals or future class variance. Collecting more examples from the
same class would not by itself validate transport to future classes.

## Generic attachment contract

The existing validator requires a curve release to be available at the requested
cutoff. This rule remains unchanged. A research scoring-identity helper accepts
canonical `LeagueRules` and preserves the existing State-based convention.
Regression coverage checks numeric normalization, scoring-row order and unchanged
wrapper behavior. This is metadata consistency, not a football-scoring change or
proof of model quality.

Model admission and real matching-State legal-package acceptance remain separate
steps. No private deployment, publication, State or Simulation evidence is included
in this public method report.

## Disposition and next step

The third-round coverage problem has been resolved for the 2019 actual-draft
sample. The remaining modeling issue is the stability and transport of a
source-qualified prior across independent classes, including its material
missing-season assumptions. The existing three-year diagnostic's advantage over
simple baselines does not establish Career reliability.

Continue under the agreed source hierarchy: qualified historical fantasy drafts,
then genuinely aggregated post-NFL-draft expert rankings where historical drafts
are insufficient. Keep individual boards and mocks as labelled sensitivity cases.
Do not treat many draft examples as many classes, silently import 1-QB overall
ranks as Superflex ranks, or select smoothing/anchors to make observed curves look
more appealing. Existing conditional-entry research did not establish a superior
alternative; that result must not be ignored when considering another estimator.

After model/source admission, use a producer-owned canonical release and an
eligible matching-State publication for legal-package acceptance. A newer refresh
alone would not resolve the model-evidence issue. Preserve the annual freeze,
current ownership/origin probabilities, historical versions, and the existing
Value → Decision → Search boundaries.

The separate directed-preference feature has passed its full suite, but remains
unmerged and undeployed under the user's valuation-dependent release objective.
No decision to deploy an unvalidated prior has been inferred from that objective.
