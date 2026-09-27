# Current Football-State H3 Research Reproducibility

Date: 2026-09-27

Research branch:
`research/current-football-state-h3-20260926`

## Historical validation
- workflow run: `36288913771`
- head: `acf49a5a3b55b948c6836866d2eb0ab62a8184da`
- artifact: `10921183161`
- digest: `sha256:154ef6c7d35d5c04ac01cfbaedd47b8a654c43dd521e4251718277a10e929ea1`

Evidence:
- 4,793 injury episodes;
- 7,603 non-injury events;
- chronological holdouts 2018-2021;
- 70,401 injury-report rows;
- 297,999 snap rows;
- 546,828 weekly-roster rows;
- 232,735 weekly-stat rows;
- snap identity mapping rate 99.942%, with no manual/name-based mappings and zero PFR→GSIS conflicts.

## Current provider capture
- workflow run: `36288669957`
- head: `acf3044112e279efd944afaf27a3e9cf94fcc9fc`
- artifact: `10921722146`
- digest: `sha256:778a47c68f3a7e6e6e2a1181dd085d8ad896e7ae8d2ab28d358b6b58b33c1329`
- capture time: `2026-09-27T02:30:40.466924+00:00`
- Sleeper state: 2026 Week 3, completed through Week 2.

## Frozen protocol/gates
- `RESEARCH_PROTOCOL.md`
- `VALIDATION_GATES.md`

The event-specific gate audit applies the same predeclared >=2% / <=5% / sample / chronology criteria uniformly to the predeclared event cohorts. It is not a named-player or current-season tuning exercise.

## Authority guards
- production H3 changed: no;
- Market inputs: no;
- Owner inputs: no;
- fantasy-trade inputs: no;
- Team Utility inputs: no;
- current provider capture promoted to deployment authority: no.
