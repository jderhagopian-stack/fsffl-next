# FSFFL Fundamental Intrinsic Value v4

Status: production candidate in PR #138; do not merge without management approval.

## Canonical definition

FSFFL Intrinsic Value estimates a player's team-independent long-term dynasty asset worth from football fundamentals alone.

It is intentionally distinct from:

- Broad Market Value: external dynasty market pricing;
- League Market Value: future league-specific pricing;
- Team Utility: roster/context-specific value;
- lineup replacement surplus: downstream roster economics;
- owner behavior or transaction acceptance.

Broad Market, Intrinsic, and future League Market may share a readable 0-10,000 presentation language, but none is numerically trained to another.

## Authority chain

`canonical State -> governed Forecast career distribution -> discounted career value -> residual fundamental information -> Fundamental Intrinsic -> display normalization`

Forecast owns football production, uncertainty, survival/attrition, role-transition trajectory, and career-state probabilities. Value consumes those distributions exactly once.

## Canonical State repair

`PlayerState` preserves PIT-safe provider facts when available:

- age;
- NFL experience / accrued seasons;
- draft year;
- draft round;
- exact draft number.

Missing facts remain `None`. Value does not reach around canonical State into raw provider payloads.

## Forecast baseline

The v4 conditioning baseline is the governed three-horizon Forecast path:

- Y1: authoritative current full-season distribution;
- QB Y2/Y3: Forecast-owned meaningful-starter career-state probabilities when available;
- RB/WR/TE Y2/Y3: governed bounded career-transition distributions according to the frozen horizon policy;
- distribution evidence: Y1/Y2/Y3 means and uncertainty;
- non-QB transition evidence: survival, conditional production transition, and observed transition dispersion.

The production residual calibration freezes this Forecast vector before fitting Value residuals.

## PIT residual calibration

Calibration version: `fundamental-intrinsic-residual-calibration-v1`.

Historical football-only panel:

- 14,876 PIT player-seasons, 1999-2024;
- 8,196 usable career-value examples, 2005-2019;
- 4,979 chronological holdout predictions;
- 9 scored chronological folds;
- target: six-season discounted realized fantasy production;
- discount factor: 0.85;
- no market, replacement, Team Utility, owner, or transaction target/input.

Every candidate fundamental factor is first residualized against:

`[Y1 mean, Y2 mean, Y3 mean, Y1 SD, Y2 SD, Y3 SD, position]`.

Candidate bundles tested included experience/career state, survival/longevity, draft pedigree, and their combinations.

### Selected residual bundle

**Draft pedigree only.**

It is the smallest bundle that remained positive and stable under the production promotion rule:

- overall chronological MAE improvement: approximately 1.97%;
- fold wins: 9/9;
- QB improvement: approximately 1.28%;
- RB improvement: approximately 1.94%;
- TE improvement: approximately 1.37%;
- WR improvement: approximately 2.69%;
- elite-tail effect: effectively neutral rather than materially harmful.

Experience alone was unstable and lost on most folds. Survival improved aggregate results but degraded QB and is already materially represented in Forecast's career path. Larger bundles improved aggregate error more, but failed the smallest-stable-cross-position standard or introduced avoidable overlap. They are not production terms.

Pedigree coordinate when exact NFL draft number is known:

`P = 1 - log(1 + min(draft_pick, 260)) / log(261)`

The expected pedigree signal is estimated from the frozen Forecast conditioning vector. Only:

`P_residual = P - E[P | governed Forecast distribution, position]`

enters Value.

Missing pedigree is not silently treated as known-undrafted. The base Fundamental Intrinsic remains available with `PARTIAL` evidence and a neutral residual contribution.

## Long-term continuation beyond Y3

Intrinsic does not stop conceptually at the three-year Forecast boundary.

The PIT calibration uses six-season discounted realized football production as the long-term target. Position-specific continuation coefficients convert governed Y3 production into expected discounted post-Y3 career production:

- QB: 4.081432648866087
- RB: 4.75136298864317
- WR: 5.2555577103676425
- TE: 4.229937041212317

The continuation is:

`Continuation = 0.85^3 * Y3_mean * continuation_coefficient(position)`

and uncertainty is propagated from Y3 uncertainty using the same governed continuation coefficient. This gives younger/longer-lived profiles additional value through Forecast trajectory plus empirically observed continuation rather than an arbitrary youth bonus.

## Fundamental Intrinsic mathematical definition

Football-only six-season 90th-percentile production anchors:

- QB: 1047.4444288312498
- RB: 412.1524660625
- WR: 439.8505064812502
- TE: 291.60519133749995

For player `i` at position `p`:

`BaseCareer_i = Y1 + 0.85*Y2 + 0.85^2*Y3 + 0.85^3*c_p*Y3`

`BaseFundamental_i = 100 * BaseCareer_i / Anchor_p`

When exact draft pedigree exists:

`ResidualPedigree_i = -1.0825294743 + 28.1875252708 * (P_i - P_hat_i)`

where `P_hat_i` is the pedigree component already explained by the full frozen Forecast mean/uncertainty vector plus position.

Final authoritative raw coordinate:

`FundamentalIntrinsic_i = max(0, BaseFundamental_i + ResidualPedigree_i)`

When exact pedigree is unavailable, the residual term is neutral and evidence is marked partial rather than fabricating a penalty.

## Anti-double-counting

| Term | Authority/source | Included in Intrinsic | Anti-overlap treatment |
|---|---|---|---|
| Y1-Y3 production | Forecast | Yes | consumed once |
| Forecast uncertainty | Forecast | Yes, as uncertainty and conditioning evidence | not independently rewarded |
| survival/attrition | Forecast career path | Yes through Forecast | separate Value survival term rejected |
| age / career state | Forecast transitions/career-state | Yes through Forecast | raw age bonus rejected |
| role trajectory | Forecast | Yes through future distributions | separate role-security term rejected |
| experience | State / Forecast-relevant | No independent term | residual candidate failed promotion stability |
| draft pedigree | canonical State | Yes, residual only | Forecast-explained component removed first |
| replacement surplus | Team Utility / Decision | No | remains downstream |
| Broad/League Market | Market layers | No | prohibited input/target |
| owner behavior | Behavioral / Decision | No | prohibited input/target |

## 0-10,000 display normalization

The display scale is downstream of the frozen raw Fundamental Intrinsic coordinate.

It uses fixed football-only quantiles from the calibration population, not current league composition and not market prices:

- raw 0 -> 0;
- p10 2.54 -> 1,000;
- p25 11.48 -> 2,500;
- p50 27.05 -> 4,500;
- p75 46.87 -> 6,500;
- p90 65.97 -> 8,000;
- p97 92.31 -> 9,000;
- p99 120.44 -> 9,500;
- above p99: monotone asymptotic tail toward 10,000.

This keeps fringe, depth, meaningful, strong, premium, elite, and apex tiers visually separated while preserving model independence from Broad Market.

## API / product contract

`/api/value/intrinsic-v2` exposes the Fundamental Intrinsic successor while v1 remains available only for compatibility.

For roster players, v2 explicitly publishes:

- `AVAILABLE`, `PARTIAL`, or `UNAVAILABLE`;
- evidence state and reason;
- confidence;
- authoritative raw Fundamental Intrinsic;
- 0-10,000 Intrinsic display value;
- percentile when valid;
- uncertainty;
- key-driver summary;
- model/calibration/display/Forecast provenance.

Unavailable Forecast evidence never becomes zero and never receives a fake percentile.

## Performance

The calculation is deterministic arithmetic over already-governed Forecast distributions plus fixed calibration coefficients. It requires no Simulation, no provider request, no market lookup, and no 50,000-run work. The Franchise Value Lens remains lazy-loaded.

## Replacement surplus authority

The old v1 replacement-surplus quantity remains useful evidence but is no longer the definition of Intrinsic. Replacement and lineup economics remain downstream in Team Utility, Trade Decision, roster-impact analysis, and competitive Simulation interpretation.

## Limitations

- The production continuation target currently reaches six seasons rather than modeling an unbounded career.
- Exact pedigree is required for the residual pedigree term; missing pedigree yields a partial base estimate rather than imputation.
- Cross-horizon covariance is not published by Forecast; uncertainty uses the conservative perfect-positive dependence bound.
- The display normalization is versioned and should be recalibrated only when the underlying football-only Intrinsic evidence population materially improves, never to chase market prices.
