# 2026-09-28 — In-Season ROS Forecast Policy

## Status
**MANAGEMENT ACCEPTED — DATA CAPTURE NOW / PRODUCTION INTEGRATION AFTER RUNTIME ACCEPTANCE**

## Management decision
For the 2026 season, FSFFL will **not require an FSFFL-native rest-of-season model before using in-season Forecast**.

Production current-season expectation should use:
- actual year-to-date NFL production as observed fact; plus
- governed third-party **raw-stat ROS projections** for the remaining schedule;
- league scoring applied downstream by FSFFL.

The resulting current-season expected finish is conceptually:
`ACTUAL_YTD + GOVERNED_ROS`.

Do not double-count injuries, role changes, or other football-state effects already incorporated by governed ROS evidence.

## Immediate data requirement
Point-in-time ROS evidence is perishable and must be captured prospectively. Begin preserving, for every governed provider capture:
- provider/source identity and health;
- capture timestamp and football week;
- raw ROS stat projection by player;
- injury/availability/status evidence available at capture;
- roster/team/role context available at capture;
- actual YTD statistics and subsequent realized outcomes;
- hashes/provenance sufficient for PIT replay.

This capture may proceed as a bounded Data/Research workstream without changing production authority or blocking the active runtime corrective.

## FSFFL-native ROS research
A native ROS model is a **shadow Research program**, not a production prerequisite.

Research should compare FSFFL-native forecasts against:
- each governed third-party provider;
- the governed provider ensemble;
- simple preseason-prior baselines.

Evaluation must be PIT/historical where feasible and segmented by position, week-of-season/sample size, and underlying statistic. Promotion requires evidence that FSFFL adds predictive value; existence of a model is not sufficient.

## Development sequence
1. **Finish current runtime / Hodor acceptance first.** This remains the sole product-critical Implementation path.
2. **Start ROS PIT data capture immediately** because missing weekly snapshots cannot be perfectly reconstructed later.
3. After runtime terminal acceptance, prioritize **in-season current-year Forecast integration** (Actual YTD + governed third-party ROS) as a production feature.
4. Run FSFFL-native ROS Research/shadow evaluation in parallel once capture is established.
5. Long-Term Intrinsic remains accepted and ready, but Management may sequence the season-critical ROS integration ahead of its deployment work.
6. Do not silently blend an experimental native ROS model into production authority.

## Authority
Forecast remains owner of ROS production/uncertainty. Data owns captured facts/provenance. League scoring remains downstream. Value/Intrinsic consume governed Forecast and must not invent their own ROS adjustments.
