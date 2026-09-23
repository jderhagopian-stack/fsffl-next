# Home North Star — exact real-league acceptance coordinate

Date: 2026-09-23

This is the pre-merge real-league sanity evidence required for the Home North Star. It was captured through the authorized production persistence connection, not by recomputing Home-specific model truth.

## Exact production coordinate

- League: `sleeper:1312071960615731200`
- Canonical State: `6163a1c95f5fed2f9591331885a6e4f43e098028c68f33d747393b5529b81dd6`
- State as-of: `2026-09-23T20:32:58.099774Z`
- Matching persisted Simulation computed: `2026-09-23T20:36:25.895928Z`
- Simulation analytics model: `next8-live-simulation-analytics-v8:resilience-driver-identity`
- Simulation runs: **50,000**
- Managed team: **jimmygoodjob** (`sleeper:1312071960615731200:team:9`)

The persisted Simulation scope ID equals the canonical State hash above, so the evidence is exact-State matching.

## Home facts verified against authoritative destination evidence

| Home fact | Exact governed evidence |
| --- | --- |
| Current record | **2-0** |
| Current league rank | **#3 of 12** |
| Competitive state | **contender** |
| Clearest roster pressure point | **RB** — rank **#9 of 12**, Strength Index **72.0893573325** |
| Projected final wins | **8.90314** |
| Playoff probability | **0.82918** (82.918%) |
| Championship probability | **0.1332** (13.32%) |
| Expected finish | **4.0863** |
| Largest single-player lineup-drop exposure | **Lamar Jackson** (`sleeper:player:4881`) — **47.5225 projected points** |

Accepted position-strength evidence for the managed team:

| Position | Rank | Strength Index |
| --- | ---: | ---: |
| QB | 2 / 12 | 112.3359831001 |
| RB | 9 / 12 | 72.0893573325 |
| WR | 1 / 12 | 139.2538163113 |
| TE | 7 / 12 | 93.1646271665 |

The Home pressure-point rule therefore deterministically selects **RB** from the single comparable QB/RB/WR/TE position-strength family. It does not compare RB weakness against fragility, Value, Market, or Simulation probabilities.

The compact Around-the-League slice resolves to:

1. **#2 jder52** — 2-0
2. **#3 jimmygoodjob** — 2-0
3. **#4 Anthonyder** — 1-0-1

## Authority verification

- Current standings are recomputed from canonical completed matchups using the accepted League Atlas ordering contract: win percentage, then points for.
- Position rank and Strength Index are read from the persisted Team View produced by the existing position-strength authority.
- Fragility drop and driver identity are read from persisted Team Utility roster resilience.
- Expected wins, playoff probability, championship probability, and expected finish are read from the matching persisted 50,000-run Simulation.
- Home creates no Forecast, Simulation, Value, Search, Decision, recommendation, acceptance probability, owner-interest estimate, or cross-family master score.
- The Market CTA carries only team + position context. Market owns Search/evaluation after navigation.
- League Atlas contextual links carry team + section + metric/position/player intent only; they do not alter destination evidence.

## CI environment boundary

The GitHub Actions environment for this repository currently does not expose `FSFFL_DATABASE_URL`. The focused Home workflow therefore cannot independently re-query production persistence. It performs all deterministic Home/navigation/API regression gates and records that access boundary. This exact production-coordinate sanity was completed through the already-authorized production persistence connector before merge. The checked-in evidence is not used by the product at runtime and creates no new authority.
