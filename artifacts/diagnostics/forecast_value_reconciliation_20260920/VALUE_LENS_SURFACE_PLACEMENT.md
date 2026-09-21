# Broad Market vs Shapley Intrinsic — non-Atlas surface placement

Date: 2026-09-20

Management asked where the direct comparison should appear outside the future League Atlas without doing a broad UI rollout in this reconciliation task.

## Recommended placement order

### 1. Player detail — strongest next home

Player detail is the cleanest non-Atlas location for the direct comparison because one asset is already the object of attention.

Recommended compact block:
- Broad Market percentile;
- FSFFL Intrinsic (Shapley) percentile rank;
- rank difference;
- expandable exact Intrinsic raw quantity/provenance;
- explicit note that the two raw scales are not commensurate.

This should not create a recommendation. It is a diagnostic read.

### 2. Players & Assets — optional comparison lens, not default master sort

Players & Assets may expose:
- Broad Market;
- FSFFL Intrinsic;
- Difference;

through an explicit lens/toggle or secondary columns.

Do **not** silently replace the current default sort with either Market or Intrinsic in this task. The current Cardinal sort has a separate market-cardinal/accounting meaning and management has not selected a new default universal value authority.

### 3. Market / Opportunities — already appropriate

The existing Market-vs-Intrinsic disagreement discovery is already the correct use:
- discovery only;
- percentile/rank comparison;
- no raw subtraction;
- no automatic buy/sell command;
- handoff into governed Search/Decision.

No duplicate new surface is required here.

### 4. Franchise / My Team — hold direct migration

The current Franchise Value Lens uses legacy `/api/value/intrinsic-v1`, which asks a different economic question from Shapley Intrinsic.

Do not silently replace that endpoint.

Until management chooses whether to retire legacy replacement-surplus Intrinsic or retain both coordinates, Franchise should:
- keep the legacy lens explicitly named/described;
- avoid calling it the canonical Shapley Intrinsic view;
- not add a second overlapping Shapley panel merely to force parity with Market/Atlas.

### 5. Home — not a primary comparison surface

Do not add the two-lens comparison to Home by default. Home should surface an already-governed opportunity/decision when one matters, not introduce another universal value dashboard.

## Atlas consequence

The future Atlas should use:
`Broad Market | FSFFL Intrinsic (Shapley) | Difference`

at player/distribution level, with Forecast-backed position strength, Simulation outcomes, and fragility as separate governed layers.

Cardinal may appear only as an explicitly named market-cardinal/accounting lens if management wants it there. It must not become the Atlas master value by implementation inertia.
