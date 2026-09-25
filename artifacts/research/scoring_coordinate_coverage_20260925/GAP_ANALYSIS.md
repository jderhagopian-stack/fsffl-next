# FSFFL NEXT — Scoring Coverage Gap Analysis

Date: 2026-09-25  
Workstream: Forecast Research  
State: research findings; no production authority change

Companion artifacts:
- `SCORING_COORDINATE_REGISTRY.csv`
- `PLATFORM_COVERAGE_MATRIX.csv`
- `PRIMARY_SOURCE_LEDGER.md`
- `IMPLEMENTATION_HANDOFF.md`

## Executive finding

FSFFL's current scoring architecture is **strong for conventional QB/RB/WR/TE linear scoring and structurally strong for the newly implemented K/DST coordinate family**, but it is not yet league-agnostic across the scoring surfaces documented by major fantasy platforms.

The main deficiency is not one missing scoring key. There are four different kinds of gaps:

1. **missing football coordinates** — attempts, completions, first downs, targets, return stats, IDP, etc.;
2. **missing scoring semantics** — position predicates, thresholds, ranges, cumulative/non-cumulative stacking, fractional/negative policy;
3. **missing distributions** — per-game milestone and PA/YA bucket expectations cannot be computed from season means;
4. **missing subject families** — current State supports QB/RB/WR/TE/K/DST only; IDP, punter and head-coach/team-offense formats require explicit subject/roster support.

The correct solution is a canonical scoring-coordinate registry plus a governed scoring-rule contract. It is **not** a growing set of platform-specific if/else statements inside Forecast.

## Current FSFFL audit

### State / League Configuration

Current:
- `Position = QB/RB/WR/TE/K/DST`.
- `RosterSlot = QB/RB/WR/TE/FLEX/SUPERFLEX/K/DST/BENCH/TAXI/IR`.
- `ScoringRule` contains only:
  - `stat: str`
  - `points: float`
- Sleeper ingestion preserves every numeric `scoring_settings` entry as a generic `ScoringRule`.

What this does well:
- an unfamiliar Sleeper numeric rule is not silently dropped at ingestion;
- ordinary coefficient-based rules can remain provider-neutral after a mapping exists.

What it cannot represent cross-platform:
- position predicates such as TE premium or RB/WR/TE-specific first-down bonuses;
- threshold predicates such as 300+ passing yards;
- inclusive/exclusive ranges;
- cumulative vs non-cumulative nested bonuses;
- fractional-scoring policy;
- negative-yardage clamp policy;
- conditional expressions such as MFL's completion-percentage rule with a minimum-attempt condition;
- platform semantic profiles for D/ST points/yards allowed;
- roster subjects such as DL/LB/DB/P/HC/team offense.

**Conclusion:** State ingestion is flexible at the raw Sleeper key/value boundary, but the canonical rule model is not yet a cross-platform scoring language.

### Forecast coordinate vocabulary

Current ordinary offense:
- pass yards/TD/INT;
- rush yards/TD;
- receptions/receiving yards/TD;
- fumbles lost.

Current K:
- attempts/makes/misses;
- detailed made/miss distance bands;
- 50+ and 60+ distinctions;
- FG yardage;
- XP attempts/makes/misses.

Current D/ST:
- broad team-unit events, returns, pressure/coverage, tackles, drive outcomes;
- distributional evidence contract for PA/YA buckets.

Major missing offensive coordinates:
- pass attempts/completions/incompletions;
- sacks taken;
- passing/rushing/receiving first downs;
- direct pass/rush/rec 2PT events;
- pick-six thrown;
- rushing attempts;
- targets;
- fumbles separate from fumbles lost;
- player return yards/TD;
- direct offensive fumble-recovery TD;
- long-play event counts;
- per-game yardage/volume distributions.

Major missing subject families:
- IDP;
- punter;
- head coach/team offense.

### Ordinary offensive scoring engine

`src/fsffl/forecast/league_scoring.py` currently maps only:
- pass yards/TD/INT;
- rush yards/TD;
- receptions/receiving yards/TD;
- fumbles lost.

Current direct 2PT scoring is **not** raw evidence. Pass/rush/rec 2PT is represented by a bounded provisional residual proportional to TD count.

Rare player fumble/ST events are also represented by bounded priors rather than native coordinates.

This is acceptable as an explicitly governed provisional path for already-authorized leagues, but it is not a league-agnostic end state because several major-platform defaults directly score 2PT and return/fumble-recovery TD events.

### K/DST scoring engine

The K/DST contract is substantially more extensible:
- rule-to-coordinate requirements are explicit;
- exact algebraic transforms are explicit;
- source independence is coordinate-specific;
- PA/YA buckets require distributional evidence;
- D/ST is a team-unit subject, not a human player.

This should be the template for the broader registry.

Remaining K/DST architecture gaps exposed by the cross-platform audit:
- linear points-per-point-allowed and points-per-yard-allowed need explicit canonical coordinates;
- D/ST attribution semantics need a platform semantic profile;
- category-specific return TD distinctions may be needed where a platform scores them separately;
- team-unit defensive metrics must never be reused as IDP-player metrics.

### Provider acquisition / normalization

Current ordinary-offense provider adapters normalize a narrow set of fields before Forecast sees them. The shared canonical map keeps only:
- pass yards/TD/INT;
- rush yards/TD;
- receptions/receiving yards/TD;
- fumbles lost.

That means richer provider-native fields can be lost **at acquisition/normalization time**, before a later league can ask for them.

This is a preventable information-loss problem.

SportsDataIO's current documented NFL projection schema proves that commercial projection products can expose, among other fields:
- pass attempts/completions/sacks;
- rush attempts;
- receiving targets;
- direct pass/rush/receive 2PT;
- fumbles;
- individual defensive tackles and defensive touchdowns.

Research does not authorize SportsDataIO or any other provider. The architectural conclusion is: **when rights permit, preserve the provider's raw coordinate superset before selecting the subset needed by today's league.**

### Historical / realized-stat layer

Positive:
- `SleeperWeeklyStatsSource` stores arbitrary numeric provider stat keys in a generic mapping rather than hard-coding only current Forecast metrics.
- nflverse-based K reconstruction already demonstrates event-level canonicalization.
- K/DST calibration harnesses already use explicit fingerprints.

Gaps:
- arbitrary Sleeper keys are not yet normalized through a governed cross-platform coordinate registry;
- ordinary-offense historical replay is still centered on the current narrow Forecast vocabulary;
- D/ST realized reconstruction intentionally omits several semantics;
- there is no IDP realized-family contract;
- nonlinear weekly bonuses require per-game truth and cannot be reconstructed from season totals alone;
- platform-specific D/ST attribution must be retained/reproducible for historical replay.

## Capability taxonomy

Capability must be evaluated at:
`league × scoring rule × subject family × forecast horizon × evidence time`.

### FULL

A rule is FULL only when:
1. the platform rule maps unambiguously to canonical coordinate(s) and rule semantics;
2. the subject type is supported;
3. Forecast has exact or governed distributional evidence for every material coordinate;
4. required source independence/rights are satisfied;
5. exact transforms are provenance-preserving;
6. uncertainty/calibration is compatible with the scoring fingerprint when simulation-grade authority is required.

A league fantasy-point total is authoritative only when **all active material rules for that subject are FULL**.

### PARTIAL

Use PARTIAL for diagnostics when:
- the rule maps to canonical coordinates;
- some, but not all, required Forecast/data/uncertainty evidence exists.

PARTIAL must identify missing coordinates/reasons.

**PARTIAL does not authorize publishing a knowingly incomplete fantasy-point total as authoritative.**

### UNSUPPORTED

Use UNSUPPORTED when:
- the rule cannot be represented by the canonical rule contract;
- the asset/subject family is unsupported;
- required semantics are unknown rather than merely unevidenced.

The product should say exactly why:
- `missing_forecast_coordinate`;
- `missing_distributional_evidence`;
- `unsupported_subject_family`;
- `unsupported_rule_semantics`;
- `platform_semantics_unresolved`;
- `insufficient_independent_sources`;
- `rights_not_cleared`;
- `uncertainty_not_compatible`.

## Nonlinear scoring audit

Several documented rule families violate the assumption that a season expected total can simply be multiplied by a coefficient.

Examples:
- 300+/400+ passing game;
- 100+/200+ rushing/receiving game;
- 25+ completions;
- 20+ carries;
- IDP 10+ tackle / 2+ sack bonuses;
- D/ST PA/YA buckets;
- punt-average ranges;
- MFL conditional predicates;
- non-fractional per-period yardage scoring.

For these rules:
`score(E[X]) != E[score(X)]` generally.

Required Forecast evidence is a per-game distribution, bucket probability, event-count distribution, or a governed joint distribution.

Combined rush+receiving bonuses require a **joint** game distribution, not independently modeled marginals blindly added together.

## Platform-semantics audit

Some platform rule names are not merely mathematical transforms of an NFL box-score total.

D/ST points allowed is the clearest example:
- Yahoo documents its own inclusion/exclusion rules;
- Sleeper documents its own PA semantics;
- ESPN has its own D/ST scoring definitions.

Therefore `POINTS_ALLOWED` needs both:
1. football event/data evidence; and
2. a `ScoringSemanticProfile` owned by the league/platform adapter.

Do not hide platform semantics inside Forecast provider code.

Similar care is required for:
- defensive vs special-teams TD attribution;
- player vs team special-teams credit;
- blocked-kick treatment;
- category stacking.

## Provider-acquisition gap analysis

### Preserve now when available and permitted

High-value raw projection fields to retain even if a current FSFFL league does not score them:

**Passing**
- attempts;
- completions;
- sacks taken and sack yards;
- first downs;
- direct 2PT;
- pick-six thrown if provider exposes it;
- long completion/long-TD event counts, not only longest play.

**Rushing**
- attempts;
- first downs;
- direct 2PT;
- long-rush/long-TD event counts.

**Receiving**
- targets;
- first downs;
- direct 2PT;
- reception-length event counts;
- long-TD event counts.

**Turnovers / special teams**
- fumbles and fumbles lost separately;
- offensive fumble recoveries/TDs;
- kick and punt return attempts/yards/TDs;
- player special-teams FF/FR/tackles if available.

**K**
- attempts/makes/misses;
- maximum available native distance granularity;
- kick distance or distance event counts;
- XP attempts/makes/misses.

**D/ST**
- all event components;
- return yards;
- PA and YA;
- provider-native game-by-game projections/distributions where available;
- attribution metadata.

**IDP**
- solo/assist/total tackles;
- sacks/sack yards/TFL/QB hits;
- INT/return yards;
- FF/FR/return yards;
- safety/block/PD;
- defensive TD.

### Preserve raw evidence before canonical reduction

Recommended provider artifact shape:
- provider/source version;
- rights class;
- captured/effective timestamps;
- horizon;
- subject identity;
- original provider field name;
- original numeric value;
- canonical coordinate mapping, nullable;
- mapping version;
- content hash/provenance.

A provider field may remain unmapped without being discarded.

This allows future registry expansion without pretending a later mapping existed at capture time.

## Historical retention gap analysis

For future replay/calibration, persist:
- raw provider projection coordinate supersets at PIT;
- canonical mapping version used at the time;
- league scoring configuration and semantic profile version;
- weekly realized raw football stats;
- event/PBP references needed for attribution;
- exact transform/scoring fingerprint;
- provider independence graph;
- uncertainty model/fingerprint.

Minimum historical datasets needed for the expanded registry:
- pass attempts/completions/sacks;
- rush attempts;
- targets;
- first downs by type;
- 2PT events;
- fumbles;
- returns;
- IDP;
- weekly yardage/volume outcomes for threshold bonuses;
- D/ST PA/YA under replayable semantic attribution.

The annual preseason artifact should remain **league-agnostic and coordinate-rich**, not store only the fields required by the league that happened to trigger capture.

## Priority framework

Priority is based on documented defaults/presets, repeated custom availability across major platforms, current commercial contest use, architectural leverage, and implementation cost. It is **not** a claim about percentage of leagues.

### P0 — close before claiming broad league-agnostic scoring

1. **Canonical Scoring Coordinate Registry and Rule Contract v2**
   - linear;
   - exclusive/cumulative bucket;
   - threshold;
   - position predicate;
   - stacking policy;
   - fractional/negative policy;
   - platform semantic profile.

2. **Direct 2PT / player return TD / offensive fumble-recovery TD**
   - scored in multiple major-platform defaults;
   - replace provisional inference where direct source evidence is available.

3. **Per-game yardage milestone distributions**
   - ESPN/NFL/Sleeper custom;
   - DraftKings 2026 Best Ball default;
   - high leverage for simulation.

4. **D/ST semantic profiles + PA/YA distribution framework**
   - already partially built;
   - make platform semantics explicit.

5. **Raw provider superset preservation**
   - cheap relative to reconstructing lost historical data later.

6. **Capability diagnostics**
   - FULL/PARTIAL/UNSUPPORTED with precise reasons.

### P1 — common configurable/commercially material expansion

- pass attempts/completions/incompletions/sacks taken;
- rush attempts;
- first downs;
- targets;
- fumbles separate from lost;
- player return yards;
- position-sensitive PPR / TE premium;
- linear D/ST PA/YA;
- core IDP subject/roster/Forecast family;
- D/ST/IDP return yards and pressure stats.

### P2 — broader advanced customization

- long-play event-count bonuses;
- reception-distance buckets;
- combined rush+rec milestones;
- drive-outcome D/ST;
- position first-down bonuses;
- IDP threshold bonuses;
- advanced K yardage/miss structures already representable but provider coverage remains sparse.

### P3 — representable but fail closed initially

- punter scoring;
- head-coach scoring;
- arbitrary MFL conditional predicates;
- unusual team-offense/team-position subjects;
- highly bespoke cumulative formulas.

P3 should be **architecturally representable** in configuration and capability reporting without forcing Forecast to invent evidence.

## Deterministic acceptance fixture suite

### F1 — conventional PPR
Core QB/RB/WR/TE linear scoring. Must remain regression-identical.

### F2 — Yahoo default half-PPR + K + D/ST
Tests half-PPR, K distance bins, return TD, fumble-recovery TD, PA buckets, fractional/negative policy metadata.

### F3 — ESPN custom volume
Points per completion, pass attempt, sack taken, rush attempt and target. Missing provider inputs must identify exact coordinate gaps.

### F4 — Sleeper TE premium
Base PPR + TE reception bonus. Uses one `RECEPTIONS` Forecast coordinate plus a position predicate; no duplicate TE reception forecast.

### F5 — points per first down
Passing/rushing/receiving first downs with position modifiers.

### F6 — DraftKings-style milestone scoring
300+ pass, 100+ rush, 100+ receive bonuses. Season mean alone must fail; per-game bucket probability required.

### F7 — long-play stacking
A 55-yard passing TD under a platform whose 40+ and 50+ TD bonuses stack. Verify explicit stacking policy.

### F8 — exclusive receiving distance bands
A 35-yard reception may receive exactly one distance-band bonus where platform semantics are exclusive.

### F9 — fractional disabled
54 rushing yards at 1 point per 10 yards with non-fractional per-period scoring must not equal a linear 5.4 points.

### F10 — negative yardage disabled
A negative yardage total is clamped only when league policy explicitly says so.

### F11 — K exact aggregation
Equal-scored K distance bands may combine algebraically; unequal bands may not.

### F12 — D/ST semantic profile
Same synthetic NFL scoring plays evaluated under Yahoo and Sleeper PA semantics can yield different PA coordinates; the difference must be adapter policy, not Forecast guesswork.

### F13 — IDP core
DL/LB/DB player with tackle/assist/sack/FF/FR/PD. Current State must report unsupported until subject/slot family is implemented; never substitute D/ST team metrics.

### F14 — player vs team special teams
Return TD/yards credited separately to player and team according to configuration.

### F15 — Fantrax position-sensitive scoring
Same reception stat scored differently by player position using a predicate.

### F16 — MFL conditional
Completion-percentage threshold with minimum attempts maps to a conditional rule; if joint evidence is absent, capability is UNSUPPORTED rather than approximated.

### F17 — provider superset retention
Provider supplies pass attempts/targets while current league ignores them. PIT raw artifact retains fields; scoring output ignores them until a league rule activates them.

### F18 — unknown custom rule
Unknown provider/platform scoring rule survives raw league import, maps to explicit unsupported capability, and blocks authoritative fantasy points for affected subjects rather than disappearing.

## Key conclusion

The largest risk to future league-agnostic support is **silent information loss before scoring**, followed by a too-simple rule schema.

FSFFL should expand from:
`provider stat → current-league Forecast metric → fantasy points`

to:
`provider raw evidence → canonical football coordinate registry → Forecast evidence/distributions → canonical scoring rule semantics → league fantasy points`.

That preserves the existing authority chain while making future leagues a mapping problem rather than a model rewrite.
