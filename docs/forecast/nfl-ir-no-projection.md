# NFL IR with no remaining projection

Canonical player status previously collapsed explicit NFL IR, Out, Doubtful and
Questionable into the same coarse injury category. The shared IR-with-no-projection
fallback checked only the fantasy roster's IR slot. An NFL IR player retained on
a fantasy bench or in a starting slot could therefore block current Simulation
when both providers omitted him, despite the intended participation policy.

## Preserve the fact, reuse the shared rule

Sleeper normalization now retains explicit NFL IR as the nullable canonical
`PlayerState.nfl_injured_reserve` fact. Both roster and attached-universe paths
use the same strict raw-status parser. Coarse status remains unchanged; Out,
Questionable, Doubtful, PUP or generic injury never implies NFL IR.

The shared Forecast participation helper admits the existing low-confidence
actuals-only/zero-ROS assumption when explicit canonical NFL IR is known and no
projection row exists. This is not a declaration that every IR player is out for
the season. Any complete or partial source projection row vetoes the assumption;
valid return projections and the existing single-source completion path remain.
Past earned points are retained. Future-year models, scoring, Simulation math,
Shapley and Intrinsic formulas are unchanged. No player-name/ID exception is added.

Cards, current lineup/Simulation preparation and the existing dynamic Career
Year-1 consumer reuse that helper. Fantasy IR eligibility keeps its original
policy/version. NFL eligibility is separately fenced at 2026-11-22 05:59:44 UTC,
with dated canonical fact/provenance no later than evaluation. Missing/false or
future-dated facts do not qualify. No historical State is backfilled from chat.

## Identity and resource contract

The field defaults to unknown. Canonical serialization omits only its null form,
preserving old State IDs. Explicit true/false facts remain canonical inputs and
change the material identity, including IR entry/exit when the coarse injury
label is unchanged. Provider raw-forecast identity is unaffected by availability.
Existing saved results remain readable; a normal owned refresh captures the new
fact and prepares the new State. Reloading an old State does not invent the fact.

No new provider calls, source, service, queue, scheduler, database schema or
connection adapter. This retains one small fact in existing acquisition and
uses existing preparation/publication paths. No additional recurring cost.

## Validation and hosted acceptance

Focused checks cover both normalization paths, strict injury distinctions,
frozen pre-change State/material hashes, IR entry/exit identity, original
projection veto, policy/capture cutoffs, earned actuals and current Simulation
coverage with an NFL IR player on the fantasy bench. Reinstating slot-only
eligibility fails the new participation and Simulation regressions.

```
pytest -q tests/test_nfl_ir_no_projection.py tests/test_season_comparison.py \
  tests/test_sleeper_normalizer.py tests/test_simulation_ros_inputs.py \
  tests/test_p0_live_candidate_runtime.py tests/test_practice_squad_participation.py
```

Full-suite and exact-head gates precede promotion. After deployment, one normal
owner refresh must capture updated NFL facts and demonstrate full forward
coverage, Simulation publication, Career coverage and restart continuity. If the
provider lacks an explicit reserve fact, keep missing evidence visible; do not
infer season absence from an ordinary injury or manufacture a projection.
