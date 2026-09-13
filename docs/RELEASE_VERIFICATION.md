# FSFFL NEXT — Production Release Verification

This note defines the lightweight verification required for production-facing/private-beta work.

## Required release check

For any work expected to be live in the private beta, record and verify all four items:

1. merged GitHub `main` SHA;
2. live Render deploy SHA;
3. Render deploy status is `live` / healthy;
4. one critical product smoke check for the released slice.

A production-facing workstream is not operationally complete while the approved `main` SHA differs from the live Render SHA unless the mismatch is explicitly intentional and documented.

## Current private-beta release mechanism

The existing private-beta Render service intentionally deploys the GitHub branch `next-8-product-layer` rather than `main` directly.

Private-beta Render service:

- workspace: `My Workspace` (`tea-dae6if9t0dsc73918us0`)
- service: `fsffl-next-private-beta` (`srv-dae6k7vqj5pc73af7bt0`)
- repository: `jderhagopian-stack/fsffl-next`
- configured branch: `next-8-product-layer`
- runtime: Python
- region: Virginia
- build: `python -m pip install -e '.[web]'`
- start: `uvicorn fsffl.product.persistent_webapp:app --host 0.0.0.0 --port $PORT`

For an approved beta release:

1. verify the deployment branch is a clean ancestor of the approved `main` SHA and has no divergent commits;
2. fast-forward `next-8-product-layer` to the exact approved `main` SHA using a non-forced ref update;
3. manually trigger the existing Render service deployment without clearing build cache unless evidence requires it;
4. wait for the deploy to become `live`;
5. verify the Render deploy commit exactly matches the approved `main` SHA;
6. inspect startup/runtime logs and perform the critical product smoke check;
7. record hosted latency or other release-specific validation before selecting the next production-facing slice.

Do not force-update a divergent deployment branch, create a duplicate Render service, or silently deploy an unapproved SHA.

## 2026-09-13 deployment alignment

At the start of the release-verification workstream:

- approved `main`: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`;
- deployment branch / live beta: `f38e2f029a0d9563986635012336434a3f9beb63`.

GitHub comparison showed `main` was a clean three-commit fast-forward descendant of `next-8-product-layer` with zero divergent commits. The deployment branch was therefore advanced non-forced to `53ff3a3c...`, and Render deployment `dep-daje320jo6nc73dgfpjg` was manually triggered.

Render reported the deployment `live` at the exact approved commit `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`; build and Uvicorn startup completed successfully.
