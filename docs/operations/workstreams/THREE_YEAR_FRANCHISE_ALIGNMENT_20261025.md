# Franchise 3-Year Intrinsic source alignment — 2026-10-25

## Scope

Correct the Franchise value-lens response so its displayed 3-Year Intrinsic score and the League 3-Year rankings consume the same exact-State Career Y1–Y3 evidence, calculation, qualified player set, and publication generation. This is a presentation-source correction. The accepted Shapley discount, Career calculation, numerical references, and Career player coverage policy are unchanged.

## Confirmed defect

The Franchise `/api/league/value-lenses` response labeled the Current Shapley percentile as “3-Year Intrinsic.” The `/api/league/three-year-position-rooms` response instead calls `build_three_year_intrinsic_player_values`, which discounts Career's retained Current annual Y1–Y3 Shapley contributions and requires Career evidence bound to the current State/publication. As a result, Franchise could show a score while the 3-Year page correctly reported that its Career source was unavailable.

## Correction

- The Franchise value-lens route now uses the same `build_three_year_intrinsic_player_values` builder as the 3-Year rankings.
- The route no longer asks the separate Current Shapley coordinator to build or restore a Current-only score for this 3-Year view. Other Current Shapley consumers keep their existing owner.
- It ranks that builder's exact candidate set with the existing percentile-rank rule and maps percentiles through the existing native-market display coordinate.
- Each 3-Year response carries source, exact State, Career input fingerprint, and publication-generation identity.
- If the completed Career artifact is missing, stale, generation-mismatched, or does not satisfy the accepted Y1–Y3 coverage contract, Franchise clears the 3-Year score fields and reports the lens unavailable. A Current-only score is never shown under the 3-Year label.
- Career's holistic raw Career value and its presentation coordinate remain separate and unchanged.

## Validation

Local focused validation passed:

- Career presentation, league value lens, and Dynasty 3-Year ranking tests.
- Route-level regression verifies the Franchise route calls the canonical 3-Year builder and publishes its exact source fingerprint.
- Product-consumer regressions for player intelligence, Franchise, League comparison, Trade Center, market, and Career presentation.
- `git diff --check`.

The full stable suite, exact-head review, merge, and deployment evidence belong in this checkpoint before production acceptance is claimed. No hosted refresh, database change, Render configuration change, or paid infrastructure change is part of this correction.

## Remaining gate

Verify the Franchise endpoint and 3-Year rankings on the same active State and publication after release. They must report the same source fingerprint, same qualified player IDs, and percentile/index values derived from the same Career Current Y1–Y3 artifact. With no compatible Career artifact, both must report 3-Year unavailable while preserving independently available Broad Market data.
