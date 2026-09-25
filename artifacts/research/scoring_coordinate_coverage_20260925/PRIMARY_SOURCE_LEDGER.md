# FSFFL NEXT — Scoring Coverage Primary-Source Ledger

Date: 2026-09-25  
Workstream: Forecast Research  
Scope: league-agnostic fantasy-football scoring coordinate coverage

This ledger records the primary-source evidence used to build the Scoring Coordinate Registry and coverage matrix. A configurable option proves platform capability; it does **not** establish prevalence unless the same source identifies it as a default/public preset. Fantrax public league-rule examples prove engine capability, not platform-wide frequency.

## Sleeper

Primary source:
https://support.sleeper.com/en/articles/3998131-what-scoring-options-are-available

Documented configurable families:
- passing yards/TD/first downs/2PT/INT/pick-six/QB sacks;
- completions/incompletions/attempts;
- 40+ completions and 40+/50+ pass-TD bonuses;
- rushing yards/TD/first downs/attempts/2PT and long-play bonuses;
- receiving/receptions/first downs/2PT, reception-distance buckets, 40+/50+ TD bonuses;
- RB/WR/TE reception bonuses;
- detailed K made/miss distance bands including 50-59 and 60+, PAT, attempts, FG yards;
- extensive D/ST event, return-yardage, pressure/coverage, PA/YA, and drive-outcome rules;
- distinct team and player special-teams scoring;
- fumbles and fumble-recovery TD;
- game-yardage/volume bonuses;
- IDP stats and IDP threshold/long-return bonuses.

Important semantics documented by Sleeper:
- reception-distance bands are exclusive rather than cumulative;
- PA/YA range categories are independent/exclusive;
- blocked FG/PAT counts as a miss for the kicker;
- categories can stack where the underlying play earns multiple configured stats.

Authority implication:
Sleeper's configurable surface alone requires a canonical model beyond FSFFL's current core offense metrics and simple `ScoringRule(stat, points)`.

## ESPN Fantasy Football

Primary source, updated 2026-08-18:
https://support.espn.com/hc/en-us/articles/360003914032-Scoring-Formats

Documented public presets:
- public PPR and non-PPR;
- standard core pass/rush/receive yardage, TD, 2PT, INT;
- PPR adds one point per reception.

Documented League Manager custom categories include:
- pass completions/incompletions/attempts and sacks taken;
- 40+/50+ TD bonuses and passing/rushing/receiving yardage game bonuses;
- rushing attempts;
- receiving targets;
- return yards/TD and fumble/fumble-lost/fumble-recovery TD;
- detailed K made/attempt/miss coordinates;
- punting stats and punt-average bands;
- broad D/ST events, return yards, linear PA/YA and PA/YA buckets;
- IDP;
- head-coach win/loss/tie, points scored, and margin buckets.

Authority implication:
ESPN demonstrates three separate architectural needs not covered by the current generic rule tuple: richer raw offense, nonlinear per-game thresholds, and additional subject families (IDP/punter/head coach).

## Yahoo Fantasy Football

Primary default settings:
https://help.yahoo.com/kb/fantasy-football/yahoo-league-sln6489.html

Current default public/private setup documents:
- 0.5 PPR;
- fractional and negative yardage points enabled;
- standard core offense;
- player return TD and offensive fumble-recovery TD;
- K distance scoring;
- D/ST events and PA buckets.

Primary scoring category list:
https://help.yahoo.com/kb/SLN6490.html

Additional categories include:
- fumble;
- completions/incompletions/attempts;
- times sacked;
- return yards;
- rushing attempts;
- pick-six thrown;
- 40+ reception/completion and other long-play categories;
- IDP families.

Primary scoring-semantics FAQ:
https://help.yahoo.com/kb/fantasy-football/SLN6441.html

Important documented semantics:
- Yahoo defines its own D/ST points-allowed attribution;
- total successful FG yards may stack with distance-band FG scoring;
- fractional and negative yardage are league-level policy switches;
- offense bonus thresholds can be cumulative;
- public leagues do not score return yards by default, but private leagues may enable return-yard scoring.

Authority implication:
Fractional/negative policy and bonus stacking are scoring-rule semantics, not Forecast stats; FSFFL's current `ScoringRule(stat, points)` cannot represent them generically.

## NFL Fantasy

Primary current scoring document:
https://support.nfl.com/hc/en-us/articles/35869730981140-Scoring

Documented default includes:
- core PPR offense;
- return TD;
- offensive fumble-recovery TD;
- 2PT;
- K;
- D/ST events and PA buckets;
- fractional and negative points enabled.

Custom options include:
- pass attempts/completions/incompletions/sacks;
- game-yardage bonuses and long-TD bonuses;
- rushing attempts;
- return yards;
- fumble;
- additional D/ST events/YA buckets;
- broad IDP stats including TFL, sack yards, QB hits, return yards and defensive TD types.

NFL documents nested long-TD bonuses as cumulative, while yardage game ranges are non-cumulative.

Authority implication:
NFL Fantasy independently confirms that volume, big-play, threshold and IDP coordinates are not Sleeper-only edge cases.

## CBS Sports

Current Commissioner FAQ:
https://www.cbssports.com/fantasy/football/games/commissioner/frequently-asked-questions

Current product:
https://www.cbssports.com/fantasy/games/football/

CBS currently states Commissioner leagues can choose from hundreds of scoring categories and create/tailor categories. Its public current marketing/FAQ does not expose a complete enumerated category catalog.

Current 2026 CBS IDP evidence:
https://www.cbssports.com/fantasy/football/news/jamey-eisenberg-drafts-a-downright-dominant-team-in-this-industry-idp-draft-full-results-strategy-more/

CBS's 2026 expert IDP league uses DL/LB/DB roster positions and scores sacks, interceptions, forced fumbles, fumble recoveries, passes defended, tackles and assisted tackles.

Authority implication:
- current CBS evidence confirms IDP commercial relevance;
- exact exhaustive current Commissioner category support should **not** be invented from old articles;
- a future CBS connector/import must capability-test the actual league configuration and map only observed rules.

## Fantrax

Public league-rule examples:
- https://www.fantrax.com/newui/fantasy/leagueRulesSummary.go?leagueId=ffsrevmxlla2o7qg
- https://www.fantrax.com/newui/fantasy/leagueRulesSummary.go?leagueId=fdavzrsnlljlfdvc
- https://www.fantrax.com/newui/fantasy/leagueRulesSummary.go?leagueId=k30uve3qlm0maauq
- https://www.fantrax.com/newui/fantasy/leagueRulesSummary.go?leagueId=156re5e1j615yrqa

Observed engine capabilities include:
- cumulative and non-cumulative ranges;
- position-specific scoring;
- first downs;
- pick-six penalties;
- return yards;
- long-TD/reception events;
- YAC and fumble-recovery yards;
- PA/YA bucket scoring;
- IDP.

Authority limitation:
These public league pages prove the Fantrax engine can express these rule classes. They do not prove how common any one custom rule is.

## MyFantasyLeague

Primary feature documentation:
https://php01.myfantasyleague.com/wp-new/feature-list/

MFL documents:
- 28 player/team positions, including punter, kick returner, head coach, team offense and multiple IDP positions;
- prepackaged or highly customized scoring;
- TD scoring based on quantity or length;
- decimal scoring;
- conditional scoring, including the explicit example of awarding points for completion percentage only if a minimum attempt count is reached.

Authority implication:
MFL establishes the need for an **extensible conditional-rule representation**, but not a requirement that FSFFL immediately model every exotic conditional rule. Initial implementation should represent these rules canonically and fail closed when the necessary joint Forecast evidence is unavailable.

## DraftKings Best Ball

Current 2026 scoring guide:
https://dknetwork.draftkings.com/2026/05/19/draftkings-best-ball-fantasy-football-guide/

2026 Best Ball scoring includes:
- core PPR;
- +3 for 300+ passing yards in a game;
- +3 for 100+ rushing yards;
- +3 for 100+ receiving yards;
- return TD, fumble lost, 2PT and offensive fumble-recovery TD.

Authority implication:
Per-game yardage threshold distributions are not merely unusual commissioner options; they are part of a current commercial best-ball scoring product. They are therefore P0/P1 architecture gaps.

## Projection/data availability evidence

SportsDataIO current NFL data dictionary:
https://sportsdata.io/developers/data-dictionary/nfl

The documented projection/data schema demonstrates that richer raw inputs are technically available from commercial data products, including:
- pass attempts/completions/sacks;
- rush attempts;
- receiving targets;
- direct passing/rushing/receiving 2PT conversions;
- fumbles;
- individual defensive tackles and defensive TDs;
- D/ST points allowed and other team-defense coordinates.

This is **not** a recommendation or license decision. It proves that FSFFL should avoid throwing away richer provider-native fields merely because the current league does not score them.

## Research methodology rule

The registry uses three evidence labels:
- **default/preset** only where a current primary source explicitly documents a default/public/contest preset;
- **custom/configurable** where the platform documents the coordinate as optional;
- **engine capability example** where a public league page demonstrates expressibility but not prevalence.

No numerical popularity estimate is inferred from configurability.
