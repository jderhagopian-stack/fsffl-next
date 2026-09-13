# FSFFL NEXT — Production Release Verification

This note defines the lightweight verification required for production-facing/private-beta work.

## Required release check

For any work expected to be live in the private beta, record and verify all four items:

1. merged GitHub `main` SHA;
2. live Render deploy SHA;
3. Render deploy status is `live` / healthy;
4. one critical product smoke check for the released slice.

A production-facing workstream is not operationally complete while `main SHA != live Render SHA` unless the mismatch is explicitly intentional and documented.

## Current private-beta deployment mismatch — 2026-09-13

Repository `main` after PR #135:

`53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`

Private-beta Render service:

- workspace: `My Workspace` (`tea-dae6if9t0dsc73918us0`)
- service: `fsffl-next-private-beta` (`srv-dae6k7vqj5pc73af7bt0`)
- repository: `jderhagopian-stack/fsffl-next`
- configured branch: `next-8-product-layer`
- auto-deploy: enabled on commit
- live deploy SHA at verification: `f38e2f029a0d9563986635012336434a3f9beb63`
- build: `python -m pip install -e '.[web]'`
- start: `uvicorn fsffl.product.persistent_webapp:app --host 0.0.0.0 --port $PORT`

The desired permanent configuration is for this private-beta service to deploy `main`, so merged production work reaches the beta automatically and the release check can directly compare `main` with the live Render SHA.

The available Render automation connector does not currently expose a mutation for changing an existing service's deploy branch. Do not work around this by moving the legacy Git branch or creating a second service. Change the existing service's branch to `main` in Render, preserve all other settings, and then allow/trigger the resulting deploy.

After that deploy completes, verify the exact live SHA and perform the critical smoke/latency checks before selecting another Phase 3 development slice.
