# Overlap and dependence analysis

Adjacent Y2/Y3 origins are not independent. The same player can appear in multiple source seasons, adjacent source origins can share target football seasons, and Y2/Y3 horizons overlap in calendar time.

Primary inference rules:
- Evaluate Y2 and Y3 separately for promotion authority; do not pool horizons into one nominal sample size.
- Treat the number of distinct source origins as the independent temporal support count: 10 for primary Y2 (2014-2023) and 9 for primary Y3 (2014-2022).
- Use two-way clustered bootstrap by player_id and source_season for row-level score differences.
- Report a moving-block source-year bootstrap as temporal sensitivity; use block length 2 for Y2 and 3 for Y3 so overlapping forecast windows travel together.
- If a target-year-specific shock is material, report sensitivity clustered by target_season in addition to source-year clustering.
- Always report raw row n, distinct players, distinct source years, and distinct target years. Never present row n as independent temporal n.
- For sparse p90+/p95+ diagnostics, add leave-one-origin and leave-one-player influence tables; no single tail row/year is a standalone pass/fail authority.