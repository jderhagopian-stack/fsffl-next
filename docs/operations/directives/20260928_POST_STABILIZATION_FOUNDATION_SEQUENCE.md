# 2026-09-28 — Post-Stabilization Foundation Sequence

## Status
**MANAGEMENT PRIORITY — EXECUTE ONLY AFTER RUNTIME / ATOMIC-PUBLICATION ACCEPTANCE CLOSES**

## Immediate priority
Do not start this program while runtime stabilization remains open. The current product-critical path is still:
1. repair the managed-team hosted acceptance proof;
2. deploy the exact corrected SHA;
3. pass hosted FSFFL -> Hodor -> FSFFL plus same-State/cross-surface/team-switch acceptance;
4. pass physical iPhone/Safari smoke;
5. close runtime stabilization.

After that terminal gate, resume product/model development in the following order.

## Foundation 1 — In-season current-year Forecast
This is season-critical and comes first.

Production contract:
- actual YTD NFL statistics/points are facts;
- remaining-season expectation comes from governed third-party raw-stat ROS projections;
- FSFFL league scoring remains downstream;
- expected season finish = Actual YTD + governed ROS;
- preserve availability/status separately from conditional healthy production;
- do not double-count injury/role changes already represented in governed ROS evidence.

Start/continue prospective PIT capture immediately because weekly ROS snapshots are perishable.

A native FSFFL ROS model remains shadow Research until comparative PIT evidence earns promotion.

## Foundation 2 — Simulation 2.0 and team-of-origin draft-pick forecasting
Simulation must become more than a current-season playoff/championship calculator. It should own the governed outcome distributions needed by downstream Value and Team Utility.

For every owned future rookie pick, preserve exact identity:
- season;
- round;
- originating team;
- current owner;
- league-specific draft-order rules.

Simulation should estimate an **origin-team pick-slot distribution**, not label a pick simply early/mid/late. Inputs may include only governed upstream evidence: current standings/state, current-season Forecast, future player Forecast, roster/depth strength, age/exposure, known future assets where appropriate, and league-specific draft-order mechanics. Do not import Market prices into the football-outcome simulation.

Near-term picks may use richer team-specific evidence. Farther-future picks must widen uncertainty and regress appropriately rather than pretending today's team ranking remains precise several seasons forward.

Where draft order uses different rules for playoff/non-playoff teams, Max PF, regular-season finish, playoff finish, consolation results, or other league settings, Simulation must model the actual league rule rather than generic NFL-style draft order.

Simulation output for each pick should include:
- probability by exact draft slot where feasible;
- expected slot / percentile;
- early/mid/late probabilities only as summaries;
- uncertainty and horizon provenance;
- the origin-team/state/forecast identity used.

The production simulation upgrade should retain current-season 50,000-run behavior where feasible, but future-pick slot estimation may use a separate calibrated multi-season simulation contract if that is more defensible than forcing one simulator to own every horizon.

## Foundation 3 — Origin-aware draft-pick Value
Draft picks must no longer be valued only as generic year/round buckets.

Value should consume the Simulation-owned slot distribution and a governed point-in-time pick-value coordinate / draft-class evidence. The core calculation is distribution-aware:

`PICK_INTRINSIC = E[value(slot, draft_class, horizon)]`

This means valuing the **full slot distribution**, not simply valuing the expected slot, because pick-value curves are nonlinear.

Required separation:
- **Broad Market pick value:** external/general market lens; may remain less team-specific if the source itself is generic.
- **FSFFL Intrinsic pick value:** origin-aware football-economic value using governed slot probabilities, class strength, horizon and uncertainty.
- **League Market pick value:** later learned from actual FSFFL transaction evidence and league-specific willingness to pay.
- **Team Utility:** downstream owner/team-specific strategic usefulness; it must not rewrite the underlying pick's Intrinsic value.

Important safeguards:
- no circular use of downstream Value/Market to forecast the origin team's football performance;
- no current-value-as-historical substitution;
- uncertainty must increase with horizon;
- do not collapse a wide distribution into a falsely precise “1.05”-style label;
- if origin-team evidence is insufficient, fall back transparently to a broader round/year prior rather than invent precision.

This work should reuse/reconcile the governed Historical Pick Coordinate research rather than inventing a new arbitrary pick scale.

## Foundation 4 — Long-Term Intrinsic
Resume the already-accepted Research contract without another family search:
- Current Intrinsic = governed Y1-Y3;
- Long-Term Intrinsic = governed Y4-Y7;
- Y8 remains coarse only;
- separate rulers and uncertainty;
- no arbitrary horizon weights;
- preserve exact-vs-set-valued Forecast authority.

This adds the missing long-horizon football-economic lens without replacing Current Intrinsic.

## Foundation 5 — Historical / PIT market evidence
Strengthen the empirical base that Market, Trade and Owner Intelligence consume:
- authoritative historical transaction ledger;
- point-in-time historical roster/state context;
- point-in-time pick coordinate with uncertainty/provenance;
- package structure/concentration evidence;
- contemporaneous player/value/forecast context where reconstructable;
- owner/team identity continuity across seasons.

Do not use current values as historical substitutes.

## Foundation 6 — League Market / Owner Intelligence
Build the third economic lens after Broad Market and FSFFL Intrinsic:
- Broad Market: external universal market;
- FSFFL Intrinsic: football-economic value;
- League Market: evidence-supported value/preferences revealed inside this league;
- Team Utility remains downstream and team-specific.

Owner Intelligence should begin directionally: demonstrated positional preferences, pick appetite, consolidation/diversification behavior, roster-construction patterns, historical counterparties and package shapes. Do not fabricate precise acceptance probabilities.

## Foundation 7 — Trade Decision and strategic conflict resolution
Use the mature value stack to improve bilateral decision quality:
- legality;
- Broad Market economics;
- Current and Long-Term Intrinsic;
- League Market evidence;
- team need / roster construction before and after;
- contender/retool/rebuild context from governed Team Utility;
- pick timing and uncertainty;
- package concentration;
- bilateral counterparty effects.

Resolve disagreement among value dimensions explicitly instead of collapsing them into one opaque score.

## Foundation 8 — Market / Search / Optimization
Only after the above inputs are trustworthy should Search aggressively exploit them:
- opportunity discovery;
- roster-aware package generation;
- bounded counteroffer generation;
- market-test options;
- upgrade/downgrade paths;
- positional and horizon-specific targeting;
- owner-fit directional ranking;
- explanation of why an opportunity exists.

Search must remain downstream of Decision and must not invent economic or acceptance authority.

## Foundation 9 — Intelligence surfaces
Expose the new foundations coherently through the North Star:
- Player Intelligence: YTD + ROS + future Forecast, Current Intrinsic, Long-Term Intrinsic, Broad Market, historical production, uncertainty and deltas;
- Franchise: roster construction, value disagreement, current/future strengths and fragility;
- League Atlas: league-wide economic/competitive landscape;
- Owner Intelligence: empirical tendencies with provenance;
- Market/Trade: actionable opportunities with drill-down to evidence.

## Operating rule
For each foundation:
1. define authority and PIT evidence;
2. Research/validate where necessary;
3. shadow before promotion where authority is not yet earned;
4. implement behind explicit contracts;
5. Work red-team the governing invariant before or at PR readiness;
6. deploy and accept before moving downstream.

Do not build downstream sophistication on provisional upstream assumptions.
