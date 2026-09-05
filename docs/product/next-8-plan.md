# NEXT-8 Interactive Product Layer Plan

NEXT-8 answers: **How does a user interact with FSFFL NEXT as a private, visual product without recreating model logic in the UI?**

## Charter gate

NEXT-8 is the interactive product layer.

It may consume NEXT-7 read-only analytics/API/report contracts and invoke explicitly exposed application/runtime operations such as trade evaluation or opportunity search.

It may not:

- calculate player or pick value;
- calculate team utility or competitive outcomes;
- create trade grades, hidden opportunity scores, or acceptance probabilities;
- reinterpret NEXT-5 dispositions or NEXT-6 action authority;
- silently fill missing/provisional upstream evidence;
- place business logic in chart components or frontend state;
- commit private league/user data to source control.

The product is a control surface over authoritative upstream capabilities.

## Beta mechanism

The first beta is a private web application designed to work well in desktop and mobile browsers and be installable as a PWA later.

Target user flow:

1. authenticate;
2. select/connect a league;
3. select the managed team;
4. enter the application shell;
5. explore League, My Team, Trade Center, Opportunities, Analytics, and Reports;
6. invoke authoritative backend workflows through explicit actions;
7. inspect results with visual summaries, interactive charts, tables, drill-downs, warnings, and provenance.

The beta should be hostable behind private authentication. Runtime league data must remain outside the repository.

## Product surfaces

### Application shell

Persistent context:

- authenticated user;
- selected league;
- managed team;
- owner strategic posture;
- authoritative state/evidence cutoff;
- warning/provisional indicator.

Primary navigation:

- League;
- My Team;
- Trade Center;
- Opportunities;
- Analytics;
- Reports.

### League

Read-only league overview sourced from NEXT-7:

- team comparison cards;
- explicit metric selector;
- expected-wins/playoff/dynasty-economics charts;
- positional/roster heat-map-ready data;
- team drill-down.

No synthetic power score is permitted.

### My Team

- projected starters, bench, taxi/IR, picks;
- age and forecasts;
- typed asset values;
- lineup/resilience/competitive state;
- owner posture shown separately from calculated state;
- player drill-down links.

### Trade Center

Interactive proposal builder:

- select counterparty;
- add/remove owned player/pick/FAAB assets on each side;
- validate legal ownership;
- submit proposal to authoritative trade-evaluation backend;
- display both teams' consequences separately;
- show economics, feasibility, disposition, acceptance status/evidence;
- launch price-discovery/frontier exploration from the current proposal.

Frontend state owns only the proposed package, not the evaluation.

### Opportunities

- trade, shop, price-discovery, waiver classes;
- explicit action tiers: actionable / market-test / diagnostic;
- filters by opportunity type, counterparty, asset, action tier, and evidence state;
- drill-down to exact upstream evidence;
- no product-side opportunity rescoring.

### Analytics

- explicit named-metric rankings;
- charts, heat maps, distributions, and comparisons using NEXT-7 data;
- trade-partner intelligence;
- historical behavior views when point-in-time league/owner evidence is populated;
- selectable dimensions rather than hidden composite scores.

### Reports

- generate report-ready artifacts from NEXT-7 report contracts;
- no report-only calculations;
- same warnings, lineage, and evidence cutoff as API/dashboard views.

## Interactive visualization principles

Visual-first, evidence-accessible:

1. visual summary;
2. interactive drill-down;
3. detailed table;
4. underlying evidence/provenance.

Charts are display components only. Their data must be supplied by typed product view models derived from NEXT-7.

Initial chart families:

- categorical bar/rank charts for league-team comparisons;
- probability/competitive outlook charts;
- roster positional heat maps;
- player forecast/value trajectories;
- trade before/after comparisons;
- negotiation-frontier scatter/line views;
- draft-capital distributions;
- opportunity action-tier summaries;
- historical league/owner transaction patterns when evidence exists.

## Product architecture

### Backend

Python remains the authoritative application/runtime environment.

A thin web/API adapter will:

- authenticate/authorize requests;
- resolve selected league/team context;
- call NEXT-7 read-only analytics queries;
- invoke explicit application actions for trade/search workflows;
- serialize typed results;
- never duplicate model calculations.

### Frontend

A separate product surface consumes the adapter contracts.

Frontend responsibilities:

- navigation and layout;
- local interaction state such as selected filters or an unsent trade package;
- accessible responsive charts/tables;
- loading/error/warning states;
- drill-down and routing;
- PWA behavior later.

### Private beta deployment

Deployment must support:

- authentication with allowlisted users;
- private runtime configuration/secrets;
- outbound network access for permitted provider/runtime ingestion;
- no private league data in Git history;
- HTTPS;
- mobile-responsive UI;
- replaceable hosting provider.

No provider-specific hosting dependency becomes model authority.

## Implementation slices

### Slice 1 — product shell contracts

- routes/screens;
- persistent selected league/team context;
- navigation model;
- product warning/status area;
- explicit interaction/action definitions.

### Slice 2 — backend web adapter

- read-only NEXT-7 query endpoints/contracts;
- explicit trade/search action endpoints/contracts;
- typed error envelopes;
- authentication/authorization boundary interface;
- runtime context resolution.

### Slice 3 — frontend shell

- responsive application layout;
- navigation;
- league/team selector;
- loading/error/provisional states;
- mobile-first behavior.

### Slice 4 — My Team and League dashboards

- roster/pick tables;
- explicit metric selector;
- interactive charts;
- team drill-down;
- no frontend calculation.

### Slice 5 — Trade Center

- two-sided visual asset selector;
- authoritative validation/evaluation submission;
- bilateral result panels;
- price-discovery launch;
- frontier visualization.

### Slice 6 — Opportunities and partner intelligence

- action-tier filtering;
- opportunity cards/table;
- counterparty grouping;
- shopping and waiver workflows;
- exact reason/evidence drill-down.

### Slice 7 — Analytics and Reports

- heat-map-ready views;
- explicit rankings and charts;
- report generation/download flow;
- historical behavior surfaces when evidence exists.

### Slice 8 — private beta runtime/deployment

- authentication/allowlist;
- runtime configuration;
- provider connection flow;
- Sleeper-backed first integrated league beta;
- private hosted deployment;
- PWA manifest/installability;
- mobile/browser validation.

### Slice 9 — end-to-end beta validation

Use the user's real league as realistic adversarial validation, not calibration truth:

Sleeper -> State -> Forecast -> Value -> Team Utility/Simulation -> Trade Decision -> Opportunity Search -> Analytics -> Product.

Any generalizable failure becomes an upstream regression in its authoritative layer rather than a UI patch.

## First implementation target

Build typed product-shell contracts and navigation/context rules first, then build the thin web adapter and frontend shell on top of them.
