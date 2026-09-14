# Latest Intrinsic Result — Within-State Player Quality Repair

## Decision

**KEEP A TEMPORARILY / ONE SPECIFIC DEFECT. Do not merge PR #138. PR #137 remains superseded and must not merge.**

The bounded repair is real: explicit career-state probabilities remain intact, while each player's own future Forecast now determines quality inside each state instead of substituting the population-average state contribution. This fixes the identified within-state compression defect and materially improves chronology, but it does not meet promotion standards.

## Exact formulation tested

For Y2/Y3, the challenger uses:

`Expected future contribution = sum_s P(player enters state s) × E[player-specific structural contribution | player's Forecast lies in state s]`

and discounts those future contributions with the existing D2/Fundamental discount and governed continuation.

State-level inputs remain state boundaries, future-state probabilities, and continuation. Player-specific inputs remain the player's own Forecast mean/distribution. No market or team evidence is introduced.

The primary conditional variant introduces no new fitted coefficient. A secondary shrinkage variant used a Jeffreys half-observation reference mass (`0.5`) to partially pool conditional estimates toward the historical position/state mean; that variant was worse and is not selected.

## Chronological validation

Same PIT chronology, **6,758 holdouts / 12 folds**:

| Model | MAE | Fold wins vs A |
|---|---:|---:|
| **A** | **23.26** | — |
| Old D2 | 34.87 | 0/12 |
| Conditional within-state quality | **30.75** | **0/12** |
| Shrunk conditional quality | 33.81 | 0/12 |
| First inference-aligned D2 | 49.13 | 0/12 |
| Best direct deployable D2 | 46.10 | 0/12 |
| Role/opportunity D2 | 47.81 | 0/12 |

Conditional D2 improves materially over old D2 (**34.87 → 30.75**) and much more over the later state-probability challengers, but remains materially worse than A (**23.26**) and loses all 12 folds.

Position MAE for conditional D2: QB **61.63**, RB **34.36**, WR **28.72**, TE **11.13**. A remains better at every position: QB **54.54**, RB **24.71**, WR **19.80**, TE **9.03**.

Conditional subgroup MAE: young **47.83**, developmental **24.32**, prime **29.71**, aging **24.70**, fringe **14.12**, elite **109.51**. The elite tail remains problematic and does not establish a reason to displace A.

## Structural gates

The identified compression defect is fixed. With identical position/state probabilities but different Y2/Y3 player Forecast quality, the higher-quality synthetic player is worth **79.67 vs 65.18** (**+22.2%**).

The inverse also works. Holding the player-specific mean/distribution path fixed and changing only credible state probabilities produces **72.72 vs 37.49** (**1.94×**) in favor of the better future-state path.

Established semantics remain coherent: stable starting QB **147.20** > weak-path high-variance backup **10.54**; credible developmental QB **47.00** retains option value; strong-upside developmental WR **59.53** > weak-upside WR **15.52**.

However, the decisive synthetic failure is generic variance. Holding the mean path and state probabilities fixed, widening only the Forecast distribution raises value from **51.54 to 59.83 (+16.10%)**. Therefore the repair reintroduces a narrower version of C's free-option-value pathology inside the state-conditioned contribution.

## State calibration

The conditional-quality repair does **not** alter the state-probability model. On the comparable historical rows:

- multiclass Brier **0.12154**
- log loss **1.4494**
- argmax accuracy **35.83%**
- upward **29.07% predicted vs 37.28% realized**
- stable **37.22% vs 35.43%**
- downward **33.72% vs 27.30%**

By position, Brier / log loss / argmax are:
- QB: **0.10996 / 1.3510 / 43.99%**
- RB: **0.12456 / 1.4753 / 35.08%**
- WR: **0.12106 / 1.4364 / 35.68%**
- TE: **0.12566 / 1.4994 / 31.88%**
- young: **0.12124 / 1.4514 / 36.31%**
- developmental: **0.12911 / 1.5312 / 33.88%**

This calibration is useful context, but it does not override the final Intrinsic chronology.

## Current-player sanity

The unshrunk conditional challenger repairs all four flagged diagnostic comparisons without named-player tuning:

- **Bijan Robinson > Sam Darnold**
- **JSN > Quinshon Judkins**
- **Brock Bowers > KC Concepcion**
- **Brock Bowers > Trey McBride**

The shrinkage variant is less clean and narrowly places McBride over Bowers, another reason not to prefer it.

The JSON companion records the full requested current set with Y1/Y2/Y3 Forecast means and SDs, Y2/Y3 state probabilities, the player-specific within-state quality signal, challenger raw value, and A raw value.

## Leakage and TE premium

No Broad Market, League Market, trade, owner/acceptance behavior, real-team roster, team-specific replacement, Team Utility, or named-player fitting is used.

TE-premium remains a separate upstream Forecast/scoring-normalization propagation issue. It is not solved inside Intrinsic.

## Single next defect

**Within-state quality and explicit state probability are not yet orthogonal enough.**

The new construction correctly preserves player-specific quality, but because that quality is integrated from the player's full Forecast distribution inside each state, residual Forecast width can manufacture extra value even when explicit state probabilities are held fixed. That partially double-counts upside/optionality.

The next experiment should therefore be narrowly about a **variance-neutral player-specific within-state quality signal**—for example, a state-conditioned central/rank/residual signal whose level can distinguish high-end from marginal members of the same state without allowing generic SD to create additional state-crossing option value.

Do not reopen A/B/C broadly. Do not add youth, market, positional, or named-player bonuses. A remains the temporary incumbent.
