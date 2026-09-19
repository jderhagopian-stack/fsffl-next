# FSFFL NEXT - Forecast-wide distributional selection preregistration

This file freezes the research evaluation before inspecting new QB/WR/TE outcomes. P0 remains the production control. The only candidates are the already-frozen D0/D1 alternatives.

Primary full-cell distributional metric: raw-point CRPS. Point guardrail: ordinary raw-point MAE. High-end control: top-decile retention-ratio CRPS to reproduce the elite-RB coordinate. State calibration is evaluated separately because D0/D1 share the state-probability layer. Log score is not used: the frozen candidates serialize deterministic state-conditional point masses without a governed within-state density, so adding smoothing would constitute a new representation choice.

An alternative earns authority only if it lowers full-cell CRPS in every frozen chronological block, has a pooled 95% bootstrap CRPS improvement above zero, does not have statistically significant MAE degradation, does not materially harm an authority-supported top-decile cohort, and preserves CRPS direction without significant MAE regression on the single locked 2021-2022 replication. Otherwise P0 remains unless a material representation concern is left unresolved.

Forecast-wide classification is preregistered: A if all positions retain P0 without unresolved concern; B if exactly one position earns a frozen alternative; C if two or more positions independently earn frozen alternatives under the same proper-score standard; D if a material problem remains but frozen D0/D1 cannot safely solve it; E for reproducibility failure.

## Material unresolved concern rule

A position is marked materially concerning even if no switch earns authority when, on the frozen 2014-2020 evidence and with adequate sample support, either (a) the current P0 candidate has a two-way-bootstrap 95% interval showing negative conditional-active bias in the highest source-magnitude tertile of top-decile rows, or (b) the opposite frozen candidate has a two-way-bootstrap 95% interval showing better top-decile retention CRPS but fails the full-cell promotion standard. These are diagnostic stop signals only; neither can promote a route by itself.
