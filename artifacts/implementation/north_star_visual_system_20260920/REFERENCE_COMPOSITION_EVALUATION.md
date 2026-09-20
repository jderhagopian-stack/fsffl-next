# North Star Reference Composition — Trade Center — 2026-09-20

## Purpose

Demonstrate the candidate visual system on one bounded, high-value workflow before any League Atlas rewrite.

This reference intentionally goes beyond rearranging the existing dark cards. It changes the first-read composition, typography, negative space, bilateral comparison, evidence depth and mobile reading order while preserving the same upstream analytical authority.

## Evidence source used in rendered harness

The browser-rendered before/after harness uses exact governed repository test-fixture fields from:

`tests/test_trade_decision_evaluation.py::test_bilateral_evaluation_preserves_each_side_separately`

Fixture:
- Team A before: 8.0 expected wins, 50% playoffs, 10% first place
- Team A after: 9.0 expected wins, 60% playoffs, 15% first place
- Team A deltas: +1.00 wins, +10.0 pp playoffs, +5.0 pp first place
- Team B before: 9.0 expected wins, 65% playoffs, 20% first place
- Team B after: 8.5 expected wins, 58% playoffs, 16% first place
- Team B deltas: -0.50 wins, -7.0 pp playoffs, -4.0 pp first place
- Simulation count in the fixture: 50,000
- Proposal fixture: Team A sends Player `p1`; Team B sends Player `p2`

The harness uses the fixture identities `Team A`, `Team B`, `P1`, and `P2` rather than inventing branded teams or player identities.

The browser screenshots are component evidence, not authenticated private-beta screenshots.

## Current/baseline composition

The baseline reproduces the PR #159 product language:
- dark rounded result container;
- small uppercase labels;
- compact package boxes;
- compact bilateral bars;
- three similarly weighted summary cards;
- evidence button as another bordered control.

Its semantics are useful, but the user still reads a dashboard.

## Candidate composition

The candidate uses:
- one light editorial decision stage against the dark application shell;
- one large first-read statement;
- franchise identity above metadata;
- open package exchange separated by a rule/bridge rather than nested cards;
- large bilateral same-metric consequence landscape;
- exact signed values adjacent to each visual encoding;
- one open story rail for managed-team shift, counterparty shift and next interaction;
- methods/provenance demoted to a quiet evidence control;
- deliberate mobile reordering rather than desktop compression.

## North Star evaluation

### Can the main truth be perceived in 2–3 seconds?
**Yes, materially better than baseline.**
The eye lands on the primary stage headline, then the package exchange, then the large green/red bilateral outcome field. The reading order does not depend on parsing multiple cards.

### Is the most important visual element dominant?
**Yes.**
The decision stage and bilateral consequence field dominate the composition. Supporting actions and evidence are visibly secondary.

### Is there materially less reading?
**Yes.**
The baseline relies on small labels and repeated card copy. The candidate lets the exchange and competitive shift carry the story visually; prose is limited to one lede, one authority note and one drill-down prompt.

### Does it feel distinctive and consumer-facing?
**Yes, relative to the current beta.**
The candidate feels closer to an editorial/decision product than a technical analytics dashboard. It uses typography, whitespace, identity and composition rather than more containers.

### Is exact evidence still accessible?
**Yes.**
Every bar keeps the exact signed returned delta. The evidence/methods layer remains one interaction away. No analytical field is replaced by a decorative score.

### Does interaction invite drill-down?
**Yes.**
The production candidate keeps the upstream action state, auto-focuses the completed decision stage once per package, and retains the advanced evidence path. Reduced-motion preference is respected.

### Does mobile feel designed?
**Yes.**
The exchange becomes send -> receive vertically, each outcome becomes a self-contained team-by-team stack, the story rail becomes a deliberate reading sequence, and the primary drill-down action spans the mobile width.

## What remains transitional

- the surrounding Trade builder and the rest of the application still use the older dark dashboard system;
- this reference does not claim the entire Trade Center is visually converged;
- PR #159's compact `visual_primitives.css` styling remains transitional;
- the light editorial stage is a candidate expression of the design system, not a requirement that every future surface be light;
- official player/team image treatment remains dependent on authorized identity assets.

## Readiness for League

The system is now **credible enough to drive a League Atlas design plan**, because it demonstrates the intended hierarchy, openness, identity, graphical comparison and mobile recomposition in working code.

However, management review remains the authorization gate. Do not propagate the system across League or other major surfaces until management accepts this reference direction.
