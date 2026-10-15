undefined

## 2026-10-12 — provider identity join correction

Committed `a5a26fa577edb545275d1d7d6d5a9e3a231cfa38` to PR #454. Current projection normalization now resolves a provider row through a unique provider/external-ID reference already asserted on canonical State, with canonical position agreement; ambiguous or stale references fail closed, and existing name/team matching remains the fallback when no asserted reference exists. Added a fixture where the asserted ID survives provider alias and team drift. This addresses a concrete identity-join miss without inferring mappings.

Verification: `python -m compileall -q src/fsffl/forecast/current_normalization.py tests/test_current_projection_normalization.py` passed on the matching local implementation. The focused pytest could not run because this workspace has no pytest installation (`python -m pytest`: `No module named pytest`). GitHub reported no workflow run yet for the new head. Loader → full-cohort composition → matching-State Position & Depth E2E, frozen-reference parity, and the full materializer memory gate remain unverified; the last recorded full materializer peak is 490,928 KiB and must be rerun after the hosted callback is connected. No source acquisition or production refresh/write was run.
