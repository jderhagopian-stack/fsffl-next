# Comprehensive Y4-Y8 Historical Architecture Freeze

Date: 2026-09-26  
State: **HISTORICAL ARCHITECTURE FINALIZED BEFORE CURRENT-PLAYER INSPECTION**  
Authority: Research only. Production H3 unchanged.

## Binding untouched-holdout decision

The nested development search selected a richer 75% specialist / 25% global-continuous blend before the final holdout was opened.

The sealed final holdout then **rejected that richer architecture under the predeclared confirmation rules**.

Effective architecture for the comprehensive Research conclusion:

**`specialist | forecast10 | two_part_ridge` for every QB/RB/WR/TE × Y4-Y8 cell.**

No post-holdout retuning, breakpoint selection, feature substitution, or route repair is permitted.

## Aggregate final-holdout evidence

| Metric | Rich selected candidate | Simpler fallback | Result |
| --- | ---: | ---: | --- |
| n | 8,579 | 8,579 | same |
| RMSE | 43.603 | 44.185 | rich better by 1.3% |
| MAE | 19.797 | 18.756 | rich worse by 5.6% |
| Spearman | 0.4942 | 0.4906 | rich slightly better |
| Top-decile tail RMSE | 113.405 | 130.482 | rich better by 13.1% |
| Survival Brier | 0.12739 | 0.12829 | rich slightly better |

The richer architecture won three aggregate dimensions, but the frozen rules also required no catastrophic position × horizon cell.

It failed that rule at **QB Y8**:
- richer candidate RMSE: **100.44**
- fallback RMSE: **77.84**
- ratio: **1.290×**
- frozen catastrophe limit: **1.15×**

That single predeclared failure is decisive. Research does not rescue or re-route QB Y8 after seeing the holdout.

## Economic bridge

Using the same lineup-capacity Shapley annual deployment game:
- richer mean Shapley MAE: **16.624**
- fallback mean Shapley MAE: **16.372**
- richer mean Shapley Spearman: **0.4610**
- fallback mean Shapley Spearman: **0.4510**

The richer model slightly improves ordering and annual tail behavior but does not improve average Shapley absolute error.

## Uncertainty

The effective fallback uses development-OOF absolute-residual conformal bands by position × horizon with a monotone horizon floor.

On the untouched holdout:
- nominal 80% band actual coverage: **87.66%**
- nominal 90% band actual coverage: **94.32%**

These bands are conservative overall. Position/horizon detail remains in the machine-readable holdout evidence.

## Information-set conclusion

The comprehensive feature search is a valuable **negative selection result**:
- richer PIT football/pedigree/trajectory features contain signal in development;
- the best development architecture materially changed from the old 10-feature benchmark;
- that extra routing/feature complexity did **not** survive the untouched final confirmation gate;
- therefore the simpler Forecast-trajectory + age/experience/prior-production information set remains the defensible long-horizon Research architecture today.

This does not prove richer football evidence is useless. It proves that the tested richer architecture was not stable enough to displace the simpler model under the governed winner's-curse controls.

## Freeze discipline

The architecture was frozen before final-holdout scoring.
Current named-player Y4-Y8 shadows were prohibited through this checkpoint.
No production H3 behavior changed.
No Market, dynasty value, Owner Intelligence, Team Utility, or trade-behavior inputs were used.

Historical final-holdout workflow:
- run: `36267110470`
- head: `4be8313170181b91ea3a7c4bbf29b22beb5dca13`
- artifact: `10914389074`
- digest: `sha256:b9d9c905982f0ff9923bbdd6a8ebc7214b08811f64ea3662e7cd1d4893959de8`

**Current-player inspection is authorized only after this freeze.**
