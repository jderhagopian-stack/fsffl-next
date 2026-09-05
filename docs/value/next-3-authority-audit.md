# NEXT-3 Authority and Anti-Double-Counting Audit

This audit verifies that each economic effect entering NEXT-3 has one authoritative home and that downstream modules cannot silently reintroduce it.

| Effect / evidence | Authoritative NEXT-3 home | Enters once as | Must not also enter as |
| --- | --- | --- | --- |
| NEXT-2 football forecast | Intrinsic value | Forecast distribution transformed by an explicit `ForecastValueMapping` | Market price, transaction premium, team utility coefficient |
| Broader dynasty market evidence | Market price | Lineage-aware robust market baseline | Intrinsic football value, team fit |
| Provider disagreement | Market price uncertainty | Dispersion among independent evidence-family votes | Separate generic risk haircut |
| League rules / format | Market context / structural value environment | Format-specific context and structural scarcity inputs | A second league-specific premium in NEXT-4 |
| League observed behavioral residual | Market context | Shrunk league residual | Team strategic preference or owner posture |
| Pick landing uncertainty | Pick value | Probability mixture over slot/outcome states | Generic market-risk discount |
| Class-strength evidence | Pick value | Explicit versioned input to pick outcome model | Separate trade premium |
| Transaction friction / liquidity | Transaction price | Explicit calibrated acquire/sell mapping plus residual uncertainty | Market baseline adjustment or NEXT-4 negotiation coefficient |
| Completed one-for-one trades | Transaction calibration / validation | Pairwise clearing evidence | Fabricated per-asset scalar transaction price |
| Multi-asset package trades | Challenger research | Preserved package-level evidence | Unsupported decomposition into individual prices |
| Team roster fit / marginal lineup value | NEXT-4, not NEXT-3 | Team-specific utility | Market, intrinsic or transaction price |
| Competitive outcome simulation | NEXT-4, not NEXT-3 | Team outcome distribution | Asset market-price adjustment |
| Owner strategic preference | Downstream decision layer | Explicit user/owner posture | Calculated market or intrinsic value |

## Findings

### 1. Forecast authority is upstream and immutable

NEXT-3 consumes `ForecastValueInput` from NEXT-2. Value code does not modify forecast authority. The import-boundary regression test permits Value to depend only on State, Forecast and Value itself.

### 2. Market and intrinsic value remain distinct

`AssetValueProfile` stores market price and intrinsic value separately and permits either to be absent. The provisional calibration policy explicitly forbids substituting market price for an unavailable intrinsic estimate.

### 3. Market-source independence is governed

The source registry tracks ultimate evidence roots. The authoritative market baseline can use that registry to collapse multiple derivative providers sharing the same evidence root into one vote. Partial lineage overlap fails closed rather than receiving arbitrary fractional weights.

The initial governed catalog conservatively treats Dynasty Dealer, FantasyCalc and Stats Guy as one revealed-transaction evidence family for authoritative vote counting until corpus overlap is quantified. DynastyProcess belongs to the separate FantasyPros-consensus-derived evidence family.

### 4. Format context and league residuals are separated from structural scarcity

The intended hierarchy is global market -> format cohort -> league residual. League behavioral calibration estimates residual behavior after structural effects implied by rules are represented. A Superflex/QB scarcity effect may not be re-added downstream merely because the league also demonstrates high QB transaction demand.

### 5. Pick uncertainty has one home

Unresolved landing slot and outcome dispersion live in the pick-value probability mixture. NEXT-4 may consume the resulting distribution but may not introduce its own generic 'uncertain pick' haircut.

### 6. Transaction friction has one home

Acquire/sell offsets and transaction residual uncertainty belong only to `TransactionPriceMapping`. NEXT-3 currently has authoritative representation and research infrastructure but no unsupported universal transaction coefficient. One-for-one trades are preserved as pairwise clearing evidence; packages are not decomposed into invented prices.

### 7. Uncertainty is concept-specific

Forecast uncertainty, market-source disagreement, pick outcome dispersion, league-residual uncertainty and transaction residual uncertainty are distinct. A generic downstream risk multiplier must not be applied merely because these distributions are uncertain; any risk preference belongs to downstream utility and must consume the distributions rather than recreate their uncertainty.

## Boundary conclusion

No reviewed NEXT-3 production path requires Decision, Simulation, Search, Analytics or Presentation authority. No team-specific roster utility is implemented in the Value package. The automated import-boundary test protects this rule from regression.

The remaining empirical refinements change parameter estimates and confidence, not architectural ownership. They therefore can continue after NEXT-3 without requiring NEXT-4 to duplicate or redesign Value authority.
