# FSFFL NEXT — Private Beta / North Star Cycle — Stage 0 Checkpoint

Date: 2026-09-20

## Recovered repository authority

- Live GitHub main: `a3c8a65e45b484b342ad3b4351cc8d8d81811971`.
- Main CI run 35520008385: completed successfully.
- PR #157 is merged; PR #156 and PR #147 are also merged.
- PR #157 head `5970237813a2d16a32a18231f0a6847287b059d9` passed full CI and Private-beta Intrinsic live diagnostics before merge.
- Current main is 191 commits ahead of the currently live Render commit `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`, with zero behind/divergence in the GitHub comparison.

## Open work checked

Open PRs are older research/docs/ops surfaces. The current Forecast-vNext research PR chain remains non-production authority. No newer merged implementation supersedes current main. PR #136 contains historical release-verification documentation, but its stated Render branch (`next-8-product-layer`) is stale relative to the live Render service configuration recovered below.

## Recovered private-beta deployment state

Render workspace: `My Workspace` (`tea-dae6if9t0dsc73918us0`).

Render service:
- name: `fsffl-next-private-beta`
- id: `srv-dae6k7vqj5pc73af7bt0`
- repo: `https://github.com/jderhagopian-stack/fsffl-next`
- configured branch: `main`
- autoDeploy: `yes` / commit trigger
- runtime: Python
- region: Virginia
- URL: `https://fsffl-next-private-beta.onrender.com`
- build: `python -m pip install -e '.[web]'`
- start: `uvicorn fsffl.product.persistent_webapp:app --host 0.0.0.0 --port $PORT`

Latest live deploy:
- deploy id: `dep-dajegcbm8hqs73fvvg3g`
- commit: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- status: `live`
- finished: 2026-09-13T18:16:08Z

Therefore the private beta is **not aligned** to current validated main. Despite current Render autoDeploy configuration pointing to main, no deploy of PR #147/#156/#157-era main has occurred.

## Canonical product direction recovered

The current roadmap keeps Phase 3 active and treats UI/product work plus existing intelligence productization as one coordinated program. The North Star requires:
- Home as a personalized command center;
- Franchise as graphical team diagnosis;
- League as a visual league atlas;
- Market as contextual opportunity discovery;
- Trade Center as a bilateral decision/simulation workspace;
- Owner Intelligence as a governed behavioral dossier.

The required authority chain remains:
`Data -> Point-in-Time State -> Forecast -> Value -> Decision -> Search/Optimization -> Analytics/API -> Presentation`.

## Forecast / Market boundary recovered

- PR #156 introduced `future-forecast-contract-v1`, a model-agnostic future Forecast boundary. Current P0 is an adapter into that contract; future Forecast versions are not required to preserve P0 scenario geometry.
- PR #157 added a discovery-only Intrinsic-vs-Broad-Market rank disagreement lens. It does not create buy/sell authority, League Market Value, Team Utility, or acceptance probability.

## Stage 1 deployment target

Exact validated deployment target: `a3c8a65e45b484b342ad3b4351cc8d8d81811971`.

Because the live Render service is currently configured directly to `main`, Stage 1 should use the existing Render service and deploy this exact current branch head. No new deployment mechanism, duplicate service, or research branch is authorized.
