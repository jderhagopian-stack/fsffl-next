# FSFFL NEXT — Proposed Intrinsic Term-Structure Contract

Date: 2026-09-26  
Status: **RESEARCH CANDIDATE / NOT PRODUCTION AUTHORITY**

## Purpose

Represent universal FSFFL Intrinsic as an explicit value-over-time curve while preserving the current three-year production coordinate and the Data → Forecast → Value → Decision authority chain.

## Candidate surface

### H1 — Near-term intrinsic contribution
- Definition: current governed Year-1 Shapley contribution.
- Evidence: current authoritative Forecast.
- Authority: already contained inside current H3 decomposition.
- Presentation: may be shown as a horizon component only after product approval; no new model is required.

### H3 — Governed dynasty core
- Definition: existing `intrinsic-shapley-i1-v1`.
- Discount: frozen production 0.85.
- Authority: **current production oracle**.
- This research does not alter its model, scale, rank, uncertainty or consumers.

### H5 — Long-horizon challenger
- Definition: cumulative Shapley deployment value through Year 5.
- Y1-Y3: existing governed Forecast path.
- Y4-Y5: separate Forecast-owned long-horizon career-state production evidence.
- Research candidate family: `two_part_state`.
- Deployment economics: same lineup-capacity Shapley game; no market, owner, roster-specific utility or trade inputs.
- Discount during challenger validation: 0.85 for continuity, with 0.70/0.95 sensitivity reported.
- Authority: **challenger only** until Forecast and Value gates below clear.

### Terminal / Career
- Do not define as exact Y6-Y8 annual box scores or a perpetuity.
- Candidate semantic: a coarse career persistence / durable-role band with explicit uncertainty.
- Examples of eventual bands may describe whether meaningful value is likely to persist beyond H5, but thresholds and labels require their own validation.
- Authority: research/design only.

## H5 production gates

A future production proposal must clear all of the following:

1. **PIT chronology:** no target-year or future football evidence leaks into Y4/Y5 features.
2. **Position validation:** no position-specific catastrophic degradation. QB requires a dedicated repair because the current generic challenger improves ranking but not RMSE.
3. **Forecast uncertainty:** empirical Y4/Y5 uncertainty by position, non-zero and wider when evidence weakens.
4. **Joint uncertainty:** validate cross-year covariance or scenario-path uncertainty before publishing a precise cumulative H5 standard deviation.
5. **Current coverage:** deterministic identity and feature coverage for the governed current player universe; missing rows fail closed.
6. **H3 preservation:** H3 outputs remain byte/semantic compatible with existing production authority.
7. **Shapley parity:** the deployment economy, lineup-capacity rules, seed/permutation contract and efficiency checks must reproduce the governed H3 implementation.
8. **Discount governance:** no discount is selected from named-player aesthetics or market rankings.
9. **Current shadows:** rank/value movements must be explainable by football persistence/production evidence rather than named-player rules.
10. **Downstream containment:** Market, Decision and Team Utility consume horizon coordinates only after Value promotion; they may not manufacture them.

## Uncertainty contract

Research supports:
- annual OOT residual-error floors by position and horizon;
- a monotone non-decreasing envelope through the long horizon;
- explicit evidence-strength/coverage flags.

Research does not yet support:
- treating annual forecast errors as independent;
- summing annual variances into an H5/H8 Value variance without covariance evidence;
- a precise terminal/career standard deviation.

Therefore a future H5 output should not claim more precision than the underlying scenario evidence supports.

## Product contract

Expose separate governed coordinates or components, for example:

```
intrinsic_term_structure:
  h1:
    value
    rank
    uncertainty
    authority
  h3:
    value
    rank
    uncertainty
    authority=production
  h5:
    value
    rank
    uncertainty
    authority=challenger|production
  terminal:
    persistence_band
    uncertainty_band
    authority=research|production
```

Do not create:
- `master_intrinsic_score`;
- a hidden weighted blend of H1/H3/H5/terminal;
- a market-anchored long-horizon adjustment;
- a team-specific “Intrinsic” value.

## Downstream design implications

Once separately promoted:
- **Player Intelligence:** show a value/rank curve and why it changes.
- **Market/Search:** find players whose H5 standing materially exceeds or trails H3, without treating that as trade acceptance.
- **Trade Center:** show package horizon exchange (near-term vs durable value) on both sides.
- **Franchise:** compare roster-value concentration by horizon.
- **Team Utility:** may interpret horizon coordinates against a team competitive window downstream, but may not alter the universal coordinates.

## Current Research disposition

- H3: keep.
- H5 architecture: empirically supported enough for a bounded next validation phase.
- exact H6-H8/career cardinal value: not supported.
- terminal/career band: supported as the next research/design direction, not yet a validated production coordinate.
