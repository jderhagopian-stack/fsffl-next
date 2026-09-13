# FSFFL Intrinsic Value v1 — Production Decision

Status: **PRODUCTION CANDIDATE — PROMOTE V1 AFTER MANAGEMENT REVIEW**  
Production PR: #133  
Base main: `f38e2f029a0d9563986635012336434a3f9beb63`

## Decision

FSFFL should no longer wait for a theoretically perfect universal Year-2/Year-3 Forecast before exposing an Intrinsic Value coordinate. The best currently supported v1 combines the authoritative current-season Forecast with a frozen, position/horizon-aware deep-horizon policy and the transparent Model A economic transform.

This is intentionally a v1. It is versioned, bounded, market-independent, and explicit about lower-confidence horizons.

## Frozen Forecast-input policy

| Position | Year 1 | Year 2 | Year 3 |
| --- | --- | --- | --- |
| QB | authoritative current | conservative carry-forward | conservative carry-forward |
| RB | authoritative current | bounded career transition when governed evidence is available | bounded career transition when governed evidence is available |
| WR | authoritative current | conservative carry-forward | bounded career transition when governed evidence is available |
| TE | authoritative current | bounded career transition when governed evidence is available | bounded career transition when governed evidence is available |

When a horizon calls for bounded transition evidence but Forecast does not have governed evidence for that player/state, Forecast does **not** invent a transition. It falls that horizon back to conservative Year-1 carry-forward and records low evidence strength.

The same rule applies to every player. There is no elite-player, QB, market-rank, team-fit, contender, owner-preference, or player-name override.

For carry-forward horizons, the mean stays at the authoritative Year-1 mean. Uncertainty is not allowed to contract: if a governed bounded path exists diagnostically, v1 uses the larger of current and bounded-path standard deviation. Carry-forward horizons do not claim a cumulative survival estimate that their mean does not actually use.

## Why the methods differ by position/horizon

The single bounded materializer was not uniformly superior. On the 9,975-path governed historical panel:

- QB bounded transitions were worse than carry-forward at both Y2 and Y3, including materially worse elite-QB results.
- RB bounded transitions improved both Y2 and Y3.
- WR bounded transitions were worse at Y2 but better at Y3.
- TE bounded transitions were better at both horizons.

The v1 policy therefore selects between only the already-tested bounded materializer and conservative carry-forward. It does not introduce a fourth Forecast family.

## Hybrid Forecast validation

Frozen hybrid versus pure carry-forward on 9,975 complete historical paths:

| Metric | Carry-forward | Hybrid v1 | Change |
| --- | ---: | ---: | ---: |
| Year-2 MAE | 35.301 | **34.683** | **1.75% better** |
| Year-3 MAE | 36.251 | **32.942** | **9.13% better** |
| Cumulative MAE | 89.469 | **88.439** | **1.15% better** |
| Year-2 Spearman | — | **0.530** | stable |
| Year-3 Spearman | — | **0.470** | stable |

Hybrid cumulative error improved versus carry-forward in 10/18 historical folds. The worst fold was about 2.9% worse. This is less universal than the downstream Model A result and is why deep-horizon evidence is surfaced as confidence rather than presented as equally strong Forecast truth.

The bounded-materializer research already demonstrated approximately 81.5% Y2 and 82.3% Y3 coverage for nominal 80% intervals, with zero structural bound violations. V1 retains production's already-correct recursive uncertainty propagation.

## Model A economic calculation

For each horizon:

`surplus_y = max(0, player Forecast_y - marginal-lineup-opportunity replacement Forecast_y)`

Then:

`raw intrinsic = 1.00 × surplus_Y1 + 0.85 × surplus_Y2 + 0.70 × surplus_Y3`

The raw coordinate is **weighted expected fantasy-point surplus above replacement**. It is not normalized to market value.

Replacement is determined from the league's actual lineup structure: fixed position starters, then FLEX, then SUPERFLEX. This is the only scarcity mechanism. Survival is not multiplied again in Value because bounded Forecast means already incorporate it.

## Affine versus Intrinsic v1

The hybrid Forecast policy was reconstructed through the same Model A economics on 9,430 chronological out-of-time player/fold observations across 17 holdouts.

| Model | MAE | Relative to affine |
| --- | ---: | ---: |
| Affine production control | 37.891 | — |
| Carry-forward Model A | 29.833 | 21.3% better |
| Pure bounded Model A | 29.509 | 22.1% better |
| **Hybrid Intrinsic v1** | **28.685** | **24.3% better** |

Hybrid Intrinsic v1 beat affine in **17/17 chronological holdouts**. Its weakest fold still improved by about 13.8%.

The absolute MAEs in this reconstruction differ from the canonical PR #131 Model A benchmark because the hybrid comparison uses the bounded-materializer universe and reconstructed replacement panel. The key result is the stable relative advantage, which is essentially the same as canonical Model A's ~24.7% improvement.

## Position results

Hybrid Model A versus affine on the out-of-time reconstruction:

| Position | n | Hybrid MAE | Affine MAE | Relative change |
| --- | ---: | ---: | ---: | ---: |
| QB | 1,106 | 89.944 | 95.904 | **6.2% better** |
| RB | 2,922 | 11.820 | 28.531 | **58.6% better** |
| WR | 3,716 | 27.834 | 29.898 | **6.9% better** |
| TE | 1,686 | 18.806 | 29.967 | **37.2% better** |

### Elite-QB limitation

Elite QB remains the clearest limitation. On 260 elite-QB observations, hybrid Model A MAE was approximately **164.2 versus 161.0 affine**, about 2% worse, with rank correlation around 0.24.

V1 does **not** repair this with a QB premium or superstar rule. Instead, QB Y2/Y3 use conservative carry-forward and therefore receive **LOW** deep-horizon evidence/confidence. This is treated as a known limitation rather than a blocker because:

1. the failed bounded transition is no longer used for QB means;
2. overall QB error still improves versus affine;
3. overall Model A improvement is large and chronologically stable;
4. the weakness is explicit and versioned rather than hidden;
5. future QB Forecast improvements can replace the horizon policy without changing Value architecture.

## Structural scarcity

The reconstructed SF-versus-1QB check remains structurally correct: QB intrinsic surplus gains materially in Superflex while non-QB values are essentially unchanged. No QB premium is applied; the effect is created by marginal lineup opportunity.

## Confidence / completeness

Forecast horizon evidence is categorical rather than a fake probability:

- **HIGH** — authoritative current-season Forecast.
- **MODERATE** — governed bounded career-transition output.
- **LOW** — conservative carry-forward or bounded-evidence fallback.

Intrinsic v1 confidence is deliberately conservative: if either deep horizon is LOW, the estimate is LOW; two governed bounded horizons are MODERATE. This makes QB values LOW confidence in v1 and also makes WR values LOW because Y2 intentionally carries forward.

The estimate still exists. Low confidence means “useful estimate with weaker long-horizon evidence,” not “pretend no value can be produced.”

## Uncertainty

V1 exposes a raw standard deviation using a transparent local linearization of player and replacement Forecast uncertainty on horizons where expected surplus is positive. It does not create a new survival multiplier, scarcity multiplier, or market-derived confidence term.

No fake numeric confidence probability is emitted.

## Current-player behavior

The production candidate is designed to accept today's authoritative Y1 Forecast immediately. Where the runtime supplies governed bounded career-transition points, the frozen position/horizon policy uses them. Where that evidence is not yet materialized for a current player, the same contract produces a complete v1 path through conservative carry-forward and records LOW evidence.

Representative policy behavior is therefore deterministic:

- elite / young / veteran QB: Y1 authoritative; Y2/Y3 carry; LOW confidence;
- RB: Y1 authoritative; Y2/Y3 bounded if available, otherwise explicit carry fallback; MODERATE when both bounded;
- WR: Y1 authoritative; Y2 carry; Y3 bounded if available; LOW confidence;
- TE: Y1 authoritative; Y2/Y3 bounded if available; MODERATE when both bounded;
- replacement-level players: same policy; Model A naturally produces zero or near-zero surplus when they do not clear replacement.

No current-player value was hand-tuned and no famous-player example was used to select the policy. The hosted beta remains on `f38e2f...`; PR #133 is not deployed or merged.

## Raw versus display coordinate

V1 creates **no market-like display normalization**. The authoritative value is the raw weighted surplus coordinate on scale:

- scale id: `fsffl_intrinsic_surplus`
- version: `1`
- units: weighted expected fantasy-point surplus above replacement.

A later presentation-only monotone display coordinate may be added without changing the economics. Broad Market Value must never be used to anchor that transformation.

## Three-value product contract

The production candidate explicitly preserves separate nullable coordinates:

- `broad_market_value`
- `intrinsic_value`
- `league_market_value`

League Market Value remains unimplemented rather than being silently substituted with another coordinate. Team Utility remains downstream.

Intrinsic v1 can also be converted into the repository's existing `IntrinsicDynastyValueEstimate` / `AssetValueProfile` contract on its own explicit ValueScale. That lets Decision consume the new intrinsic dimension without a new composite score or broad redesign.

## Operational/versioning behavior

Versions are explicit:

- Forecast policy: `intrinsic-v1-forecast-policy-1`
- Intrinsic model: `intrinsic-value-v1`
- replacement context: `marginal-lineup-opportunity-v1`
- raw scale: `fsffl_intrinsic_surplus` version `1`.

Future evidence can replace QB deep-horizon treatment, bounded transition calibration, annual weights, or replacement calibration by versioning those components rather than redesigning the product.

The current candidate adds deterministic in-process calculations and no external provider call, database migration, or expensive simulation. Cache keys that persist v1 estimates must include the intrinsic model version, Forecast policy/base model versions, replacement-context version, league scoring/lineup state, and evaluation cutoff.

## Production recommendation

**PROMOTE V1**, subject to management review and clean PR validation.

Why:

1. it is materially better than the affine production control;
2. it wins all 17 comparable chronological Model A holdouts;
3. it removes the failed generic QB transition rather than hiding that failure;
4. it is transparent and economically interpretable;
5. it exposes weak horizons as LOW confidence instead of refusing to estimate value;
6. it preserves Market / Intrinsic / League Market / Team Utility boundaries;
7. it is explicitly versioned so future Forecast improvements can replace v1 inputs cleanly.

Known limitations are not being declared solved. In particular, elite-QB long-horizon economics remain weaker than desired and appreciation/decline remains an imperfect diagnostic. V1 ships those limitations honestly rather than adding unsupported complexity.
