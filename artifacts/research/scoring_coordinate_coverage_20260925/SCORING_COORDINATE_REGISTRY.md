# FSFFL NEXT — Scoring Coordinate Registry

Version: research-v1  
Date: 2026-09-25  
Machine-readable registry: `SCORING_COORDINATE_REGISTRY.csv`

## Purpose

The Scoring Coordinate Registry is the canonical vocabulary between:
- provider raw evidence;
- Forecast;
- league scoring;
- historical replay/calibration.

It is independent of Sleeper, ESPN, Yahoo, NFL Fantasy, CBS, Fantrax, MyFantasyLeague, DraftKings, or any individual FSFFL league.

A **coordinate** describes a football fact Forecast may need to estimate.  
A **scoring rule** describes how a league turns one or more coordinates into fantasy points.

Do not create a new Forecast coordinate merely because a platform exposes a new scoring UI label.

## Evidence shapes

### 1. Linear stat total

Examples:
- passing yards;
- receptions;
- rushing attempts;
- tackles.

Expected fantasy points can be computed from an expected total when the league rule itself is linear.

### 2. Event count

Examples:
- passing TD;
- 2PT conversion;
- return TD;
- sack.

The Forecast coordinate is an expected event count/distribution.

### 3. Event bucket vector

Examples:
- K FG distance bands;
- reception-distance bands.

Provider-native aggregate bins may combine only when the scoring transformation is algebraically exact.

### 4. Per-game bucket distribution

Examples:
- 300+ passing yards;
- D/ST points allowed ranges;
- punt-average ranges.

A season total/mean is insufficient. Forecast must provide probabilities or a per-game distribution over the relevant scoring-period coordinate.

### 5. Joint distribution

Examples:
- combined rush + receiving yard milestone;
- conditional completion percentage with a minimum-attempt threshold.

Marginal means cannot be combined as if independent when the rule depends jointly on multiple statistics.

### 6. Predicate / policy

Examples:
- TE premium;
- RB/WR/TE first-down bonus;
- fractional scoring off;
- cumulative vs exclusive bonus stacking.

These are **rule semantics**, not new football statistics.

## Canonical subject families

### Supported today
- offensive player: QB/RB/WR/TE;
- kicker player: K;
- NFL team unit: D/ST.

### Proposed expansion
- individual defensive player;
- punter;
- optional head-coach/team-result subject;
- optional team offense / platform-specific team subject.

Team-unit D/ST coordinates and individual-player IDP coordinates must remain separate even when both use labels such as sack, tackle, interception, or forced fumble.

## Rule semantics contract

The registry recommends a provider-neutral compiled rule shape with at least:

- canonical coordinate ID(s);
- scoring operator:
  - `LINEAR`
  - `EVENT_COUNT`
  - `BUCKET_EXCLUSIVE`
  - `BUCKET_CUMULATIVE`
  - `THRESHOLD`
  - `POSITION_MODIFIER`
  - `CONDITIONAL`
- scoring period: play / game / fantasy week / season;
- coefficient or point value;
- range/threshold bounds where applicable;
- subject predicate where applicable;
- explicit stacking policy;
- fractional/quantization policy;
- negative-value policy;
- semantic profile for platform-defined attribution;
- provenance to the original platform rule.

A raw platform rule must remain available alongside the compiled rule so a future registry version can be replayed without pretending the old mapping was known at capture time.

## Exact transforms

Exact transforms are governed registry metadata, not ad hoc scoring code.

Examples:
- incomplete passes = pass attempts − completions, only if both refer to the same subject/horizon/period and are complete;
- FG misses = FGA − FGM under the same condition;
- XP misses = XPA − XPM;
- K distance bins may combine when all underlying bands share the same coefficient.

Not exact:
- splitting 50+ FG into 50–59 and 60+;
- deriving long-play counts from a season yardage total;
- deriving target counts from receptions;
- converting aggregate points allowed into PA-bucket probabilities;
- converting a season mean into a weekly milestone probability.

## Rule modifiers are not duplicate Forecast metrics

### TE premium / position PPR

Forecast:
- one canonical `RECEPTIONS` coordinate.

Scoring:
- base reception coefficient;
- plus a position predicate applying an additional coefficient to TE (or RB/WR).

Do not create `TE_RECEPTIONS` as a separate forecast.

### Position first-down bonus

Forecast:
- passing/rushing/receiving first-down coordinates.

Scoring:
- a position predicate.

### Fractional scoring

Forecast:
- underlying yardage distribution.

Scoring:
- policy determines whether the per-period result is linear/fractional or quantized/floored.

## Platform semantic profiles

Some platform coordinates need explicit semantic profiles because identical labels can count different NFL events.

Initial semantic-profile family:
- `DST_POINTS_ALLOWED`
- `DST_YARDS_ALLOWED`
- team vs player special-teams attribution;
- defensive/special-teams TD categorization;
- blocked-kick categorization.

A semantic profile belongs to league configuration/scoring translation, not a provider projection adapter.

## Registry priority meaning

- **P0** — documented default/contest scoring or foundational rule semantics needed before broad league-agnostic claims.
- **P1** — repeatedly documented configurable rule family across major platforms or a core commercial subject family.
- **P2** — meaningful advanced customization with architectural value.
- **P3** — specialized rules that should be representable and fail closed before FSFFL invests in full Forecast support.

Priority does not estimate market share.

## Current capability result

The machine-readable registry classifies each coordinate/rule semantic as:
- `FULL`;
- `PARTIAL`;
- `UNSUPPORTED`.

The status is a research audit of current architecture, not production authority.

At runtime, capability must be recalculated for the actual:
`league × subject × horizon × evidence cutoff`.

A league can contain a mixture of FULL, PARTIAL, and UNSUPPORTED rules, but an authoritative subject fantasy-point Forecast must be withheld when any active material rule is not fully covered by governed evidence.

## Registry governance

Future changes should:
1. add the football coordinate once;
2. map platform rules to it through platform adapters;
3. map provider raw fields to it through provider adapters;
4. attach exact transforms explicitly;
5. define historical replay requirements;
6. define uncertainty compatibility;
7. version the mapping.

Do not let a new platform add scoring math directly to Forecast.
