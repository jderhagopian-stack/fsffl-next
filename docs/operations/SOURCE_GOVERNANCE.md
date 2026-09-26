# FSFFL NEXT — Source Governance

## Product principle

FSFFL NEXT is **provider-agnostic by architecture**.

Forecast, Value, Simulation and downstream consumers depend on canonical FSFFL contracts, not on a hard-coded third-party provider identity. Providers are replaceable evidence suppliers behind governed adapters.

A provider change must not require redesigning the core Forecast model, league scoring model, Decision layer, Simulation layer, or Presentation contract.

## Rights are source-specific and deployment-stage-specific

Provider agnosticism does not waive source terms, licenses, API restrictions, attribution duties, storage limits, redistribution limits, or other usage conditions.

Every external source must carry a rights/use classification that reflects the actual intended use.

Minimum classes:
- `RESEARCH_ONLY` — research/benchmarking only; not deployed.
- `PRIVATE_BETA_ALLOWED` — current terms/license permit the specific non-commercial/private-beta acquisition, storage, derivation and display pattern being used.
- `COMMERCIAL_ALLOWED` — current executed/self-serve terms explicitly permit the intended commercial acquisition, storage, derivation and display pattern.
- `REVIEW_REQUIRED` — terms, ownership, redistribution, derivative-use, storage or API scope are ambiguous; do not deploy until clarified for the intended use.
- `PROHIBITED` — the intended use conflicts with the governing terms/license.

A source may be eligible for private beta while still requiring commercial re-review.

## Commercial-transition rule

Any deployed source that is not classified `COMMERCIAL_ALLOWED` must carry:
- `commercial_recheck_required=true`;
- provider/source identity;
- exact terms/license URL or contract reference;
- terms/license version or captured date where available;
- permitted use summary;
- prohibited/uncertain use summary;
- storage/retention restrictions;
- redistribution/display restrictions;
- attribution requirements;
- acquisition method/API plan;
- replacement/fallback status.

Before any commercial launch, Management must re-audit every source marked `commercial_recheck_required`. A source that cannot clear commercial use must be replaced or removed without changing the provider-neutral architecture.

## Authority and evidence

Rights eligibility is separate from analytical authority.

A source can be legally/contractually usable but analytically insufficient; analytically excellent but unusable under its terms; usable in private beta but not commercial; or commercially licensable but not currently subscribed/licensed.

Forecast authority still requires the applicable semantic, source-health, independence, uncertainty, PIT/horizon and coverage rules. Rights classification neither upgrades nor downgrades analytical evidence by itself.

## Private-beta rule

Private beta does **not** mean unrestricted use. Before a source is deployed in beta, its terms/license must be checked against the actual planned use. If that use is permitted, it may be tagged `PRIVATE_BETA_ALLOWED` even if commercial rights are not yet established. If the terms are ambiguous, it remains `REVIEW_REQUIRED` until clarified.

## Provider-neutral implementation requirement

Adapters normalize provider-native evidence into canonical FSFFL coordinates while retaining provider provenance and permitted raw evidence according to the source's rights class.

No consumer should require a particular provider name when a canonical coordinate/evidence contract is sufficient.

Provider replacement acceptance should prove that a second eligible source can satisfy the same canonical contract without changing downstream domain logic.

## Management intent

During private beta, prefer technically strong, terms-compliant sources without prematurely locking FSFFL into long-term commercial contracts. Preserve enough provenance and rights metadata that a future commercial transition can replace, renegotiate, or license providers deliberately.
