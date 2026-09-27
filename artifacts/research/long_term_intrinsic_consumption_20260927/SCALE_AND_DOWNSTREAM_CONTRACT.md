# Long-Term Intrinsic — Scale and Downstream Contract

Date: 2026-09-27

## Product-facing scale

### Raw quantity

The authoritative economic quantity is retained in native units:

`raw_long_term_intrinsic = mean annual Y4-Y7 Shapley marginal fantasy-point capacity`.

For unresolved Forecast cells the raw authority is an interval:
- `raw_authority_low`;
- `raw_authority_high`.

A mechanical midpoint may be exposed as `raw_reference_center`, but must be labeled as a presentation/reference center rather than a selected Forecast truth.

### 0-10,000 ruler

Use the same **presentation convention** already used for current Shapley Intrinsic: rank-calibrate the governed eligible cohort onto a 0-10,000 Value Index.

Recommended new scale identity:
- `scale_id = fsffl-long-term-intrinsic-index`;
- `version = long-term-y4-y7-v1`;
- nominal range: 0-10,000;
- reference population: governed eligible QB/RB/WR/TE cohort for the league/evaluation coordinate.

Semantics:
- the index expresses standing **within the Long-Term Intrinsic lens**;
- percentile remains available as the transparent secondary coordinate;
- raw Shapley units remain available in drill-down;
- the index is not an additive economic quantity.

Do not use the historical 2018-2019 raw distribution as a direct fixed linear 0-10,000 calibration. Its realized long-term target is heavily zero-inflated (median 0), making a fixed raw linear ruler unstable for the active-player product population.

### Relationship to Current Intrinsic

Current Intrinsic may continue to use its existing 0-10,000 presentation ruler.

The two indexes can share visual grammar because both are rank-calibrated, but they must have distinct scale IDs and labels:
- **Current Intrinsic — Y1-Y3**
- **Long-Term Intrinsic — Y4-Y7**

Equal displayed numbers mean similar **within-lens standing**, not equal raw Shapley magnitude.

Never:
- add the two indexes;
- average them;
- subtract raw Current from raw Long-Term;
- describe one as a percentage of the other.

## Recommended product representation

For each player:

```
current_intrinsic:
  horizon: Y1-Y3
  raw
  percentile
  value_index_0_10000
  uncertainty

long_term_intrinsic:
  horizon: Y4-Y7
  raw_authority_low
  raw_reference_center
  raw_authority_high
  percentile_reference
  value_index_reference_0_10000
  annual:
    Y4 ... Y7
  model_authority_uncertainty
  within_model_uncertainty
  combined_outer_band
  authority
```

Because every current position has unresolved cells somewhere in Y4-Y7, the UI should never imply that the reference center is an exact scalar authority.

## Market implications

Market remains a separate Value/Analytics consumer.

Authorized conceptual use:
- Broad Market versus Current Intrinsic rank gap;
- Broad Market versus Long-Term Intrinsic rank gap;
- Current-versus-Long-Term durability gap.

Examples of legitimate analytics:
- “market prices near-term production more highly than FSFFL long-term capacity”;
- “long-term FSFFL standing exceeds current FSFFL standing”;
- “high model-authority width: durable value is uncertain.”

Not authorized:
- automatic buy/sell classification;
- trade acceptance probability;
- a hidden weighted blend of Market + Current + Long-Term;
- using current market values to recalibrate Long-Term Intrinsic.

## Team Utility implications

Team Utility should receive a typed vector, not a new universal scalar:

`{current_intrinsic, long_term_intrinsic, long_term_authority_width}`.

A separately governed competitive-window policy may later decide how much a specific franchise cares about each coordinate.

Thus:
- a contender may consume Current more heavily;
- a rebuild may consume Long-Term more heavily;
- but those coefficients live in **Team Utility**, not in player Intrinsic.

No contender/rebuilder weight is authorized by this Research result.

## Trade / Decision implications

Decision may expose:
- package Current-Intrinsic delta;
- package Long-Term-Intrinsic delta;
- model-authority width / durability uncertainty;
- whether a trade exchanges near-term for durable economic capacity.

It must not simply add Current + Long-Term indexes or raw quantities.

## Why this separation matters

The 335-player shadow has Current-vs-Long-Term Spearman only **0.663**, median absolute rank movement **45**, and 75.5% of players moving at least 20 ranks.

That is enough divergence to make the second lens useful. It is also enough divergence that hiding the difference in one master number would destroy information.
