# NEXT-7 Exit Review

This is the governing closeout matrix for NEXT-7 Analytics & API.

## Promotion states

- **AUTHORITATIVE** — validated enough for default read-only analytics behavior.
- **AUTHORITATIVE_CONDITIONAL** — authoritative when the relevant upstream evidence/view is supplied.
- **ABSENT_BY_DESIGN** — intentionally not fabricated without upstream authority.
- **OUT_OF_SCOPE** — belongs to NEXT-8 or another downstream product layer.

## Current classification

| Component | Status | Basis | NEXT-8 may consume? |
| --- | --- | --- | --- |
| Analytics context / state identity | AUTHORITATIVE | Exact league/state/as-of identity; generated-at separated from evidence cutoff | Yes |
| Model lineage | AUTHORITATIVE | One explicit model version per component | Yes |
| Warning/provisional propagation | AUTHORITATIVE | Missing/provisional/unknown/truncation states remain visible | Yes |
| Deterministic analytics JSON | AUTHORITATIVE | Canonical sorted serialization | Yes |
| Team analytics view | AUTHORITATIVE_CONDITIONAL | Pure join of canonical roster + supplied forecast/value/lineup/utility evidence | Yes |
| Player age/roster/projected-role display | AUTHORITATIVE | Passed through from State/NEXT-4 without recalculation | Yes |
| Draft-pick inventory view | AUTHORITATIVE | Canonical ownership only | Yes |
| League team comparison rows | AUTHORITATIVE_CONDITIONAL | Read-only summaries of supplied team views | Yes |
| Named metric league rankings | AUTHORITATIVE | One explicit metric at a time; missing evidence surfaced | Yes |
| Asset-portfolio ranking | AUTHORITATIVE_CONDITIONAL | Same NEXT-3 value scale/concept required; otherwise fails closed | Yes |
| Opportunity action-tier summary | AUTHORITATIVE | Preserves NEXT-6 action authority exactly | Yes |
| Candidate reason summary | AUTHORITATIVE | Counts explicit NEXT-6 reason codes only | Yes |
| Trade partner analytics | AUTHORITATIVE_CONDITIONAL | Descriptive counts over evaluated NEXT-5/NEXT-6 evidence | Yes |
| Trade partner named-metric ranking | AUTHORITATIVE | Explicit requested count metric only; no partner score | Yes |
| Unknown acceptance display | AUTHORITATIVE | `NOT_ESTIMATED` remains unknown | Yes |
| Report-ready league bundle | AUTHORITATIVE | Composes existing analytics views with exact shared context | Yes |
| Markdown report renderer | AUTHORITATIVE_PRESENTATION | Formatting only; no new model calculations | Yes / reusable |
| Analytics cache identity | AUTHORITATIVE | State/as-of/lineage/view identity; render timestamp excluded | Yes |
| Read-only analytics service | AUTHORITATIVE | Query/retrieve/serialize only; no mutation endpoints | Yes |
| Analytics master power score | ABSENT_BY_DESIGN | No evidence-backed upstream composite exists | No hidden use |
| Hidden trade grade / opportunity score | ABSENT_BY_DESIGN | NEXT-5/NEXT-6 structured outputs remain authoritative | No hidden use |
| Live league analytics population | PENDING RUNTIME | No live league has been executed in this chat runtime | Yes when runtime available |
| Interactive dashboard / user controls | OUT_OF_SCOPE | NEXT-8 product layer | NEXT-8 owns |

## Key safety properties

- Analytics cannot alter forecasts, values, simulation outcomes, team utility, trade dispositions, or opportunity authority.
- Unknown acceptance is displayed as unknown rather than interpreted.
- Missing teams in a named metric ranking are surfaced explicitly.
- Values on incompatible NEXT-3 scales cannot be ranked together.
- Trade partners are ranked only by an explicitly selected descriptive metric, never a hidden score.
- Report rendering uses the same read-only view fields as the API path.
- Cache identity reflects authoritative state/model identity rather than render time.
- The Analytics service exposes retrieval only and no create/update/delete interface.
- NEXT-7 has an automated import boundary preventing downstream interactive/product authority leakage.

## Controlled validation coverage

Current tests cover:

- deterministic analytics serialization;
- lineage uniqueness and timestamp ordering;
- exact LeagueState identity binding;
- roster slot, age, taxi, starter-role, and pick ownership propagation;
- future forecast filtering;
- named expected-win ranking;
- missing metric evidence propagation;
- incompatible value-scale rejection;
- opportunity action-tier and reason-count preservation;
- trade partner unknown-acceptance counts;
- explicit trade-partner ranking metric selection;
- deterministic report rendering and context parity;
- cache key stability across render times and sensitivity to model lineage;
- team-scoped query identity;
- read-only retrieval and not-found behavior;
- authority/import-boundary protection.

## Remaining runtime / product work

### 1. Live league population

The analytics contracts are ready to display a real league, but this chat runtime has not executed the live Sleeper -> NEXT pipeline. Therefore no live league report or dashboard result has been observed yet.

The integrated beta remains:

**Provider -> State -> Forecast -> Value -> Team Utility -> Trade Decision -> Opportunity Search -> Analytics/API**

A real league should be used as adversarial product validation, not universal calibration truth.

### 2. Upstream calibrated gaps remain visible

NEXT-7 must continue to expose, not repair:

- acceptance probability `NOT_ESTIMATED` until calibrated;
- production materiality policy absence where applicable;
- search truncation/non-exhaustion;
- provisional covariance/scoring assumptions;
- missing forecast/value evidence.

### 3. Interactive product layer

NEXT-8 may add:

- dashboard navigation;
- team selectors;
- trade builders;
- filters/sorting controls;
- interactive heat maps/charts;
- report export UX;
- user-specific saved views/preferences;
- runtime connection flows.

NEXT-8 must consume NEXT-7 contracts and must not recreate decision logic in frontend code.

## Exit recommendation

NEXT-7's read-only analytics/report/API foundation is suitable for closeout once final exact-head CI and changed-file scope are clean.

The phase should **not** remain open merely to invent:

- a league power score;
- a trade grade;
- a partner-likelihood score;
- acceptance probabilities;
- presentation-only value adjustments;
- interactive product behavior.

Those either require upstream evidence or belong in NEXT-8.
