# FSFFL NEXT - I1 production source dependency / substitution plan

Status: implementation handoff evidence; not a commercial-readiness claim

## Principle

I1 consumes canonical football facts, not provider-specific raw fields. Production may replace providers without changing Forecast semantics as long as the replacement maps to the same canonical contract, carries provenance/coverage, and passes canonical-data parity.

## Fact-family dependency matrix

| Canonical fact family | Current repository / validation source | Current status for this implementation | Replacement requirement |
|---|---|---|---|
| Current full-season fantasy production projection | Existing production ensemble: Razzball, FFToday, CBS, NFL Fantasy | Existing production authority already gates independent sources; provider terms/availability remain external dependencies | Any governed projection provider(s) may replace a source if normalized observations preserve the existing Forecast contract and independent-source gate |
| Player identity / team / position / basic live status | Existing Sleeper adapters / Sleeper player universe | Production-used today; status taxonomy alone is not sufficient for I1 continuity semantics | Replaceable through canonical player identity and explicit status mapping |
| Weekly organizational attachment / roster continuity | nflverse weekly-roster evidence in research/validation | Research/validation evidence; not asserted commercially production-ready here | Licensed/provider-approved weekly roster/status history mapped to active/attached/release/practice/reserve and transition counts |
| Injury / practice / non-IR availability | nflverse injury evidence in research/validation | Research/validation evidence; upstream rights/provider terms require explicit production review | Licensed injury/practice feed preserving non-IR injury vs reserve/organizational absence semantics |
| Participation / snap trajectory | nflverse stats/snap evidence in research/validation | Research/validation evidence; snap series includes upstream-derived data and is not asserted commercially ready | Licensed snap/participation feed mapped to participation, stats and snap-play coverage |
| Role / opportunity | Historical research usage panel; current validation can derive attempts/carries/targets from governed football stats | Historical calibration dependency requires rights review; production current feed not yet designated by this PR | Licensed football-stat feed supplying games plus position-appropriate pass attempts/carries/targets/receptions |
| Historical I1 calibration outcomes | Fantasy-Football-Analytics textbook seasonal stats + nflverse player identity in frozen research evidence | Frozen research oracle only; derived model parity can be demonstrated, but production use/redistribution rights must be reviewed before authority promotion | Approved historical player-season production and identity source sufficient to reconstruct frozen training rows or an approved frozen model artifact derived under cleared rights |
| Shapley structural rules | FSFFL league rules / production code | Internal governed data, no external source dependency | None beyond governed league rules |

## Important licensing boundary

This implementation intentionally does not claim that the research/validation nflverse, upstream NFL/PFR-derived, Fantasy-Football-Analytics textbook, or projection-provider data are cleared for every contemplated commercial storage/redistribution/use case. The canonical adapter is the architectural mitigation: provider replacement should not require changing I1 or Shapley.

Before commercial production authority is promoted, management/legal/provider review should resolve: (1) live weekly roster/status rights; (2) injury/practice rights; (3) snap/participation rights; (4) role/opportunity stat rights; (5) historical calibration-data rights; and (6) each projection provider's permitted production/commercial use.

## Fail-closed rule

If an approved provider cannot supply a canonical fact family, the adapter must mark the corresponding coverage false and route to the frozen reduced/fallback path. It must not infer healthy, active, retained, released, dead or non-persistent from absence. If required facts cannot be sourced safely enough to preserve frozen I1 semantics at acceptable coverage, implementation status is `BLOCKED`, not an invitation to invent provider-specific guesses.