# Manual research workflow: execution prerequisites and isolation

File: `.github/workflows/intrinsic-historical-shapley-research.yml` (draft PR #464 only).

**Isolation:** research branch guard, `workflow_dispatch` only, unique concurrency group by run ID, repository read and Actions read permissions only. Does not deploy, alter the production database, merge, or touch Codex's ongoing branches. It executes the real imported `fsffl.value.shapley_intrinsic.monte_carlo_shapley_scenarios` through `scripts/replay_historical_production_shapley.py` with 2048 permutations for 12-team Superflex and single-QB diagnostic fixtures.

**Not yet runnable as-is:** GitHub's `workflow_dispatch` requires the workflow file to be registered on the default branch. This workflow intentionally lives on PR #464, not default; DO NOT claim manual dispatch works until an explicit, authorized safe default-branch registration occurs. Also the required input Actions artifact, name `intrinsic-historical-panel-authorized` containing `player_season_panel.csv`, has NOT been provisioned or independently verified. The CSV lives in the user's persistent ChatGPT Library; GitHub runners cannot directly access that Library. No historical run has been triggered or completed.

**Safe enablement choices requiring explicit authorization:** register a dispatch-only workflow on default without merging research code, whose job checks out the exact research SHA (never an arbitrary branch), and provision a restricted, approved historical-data artifact from an authorized source. Do not upload historical datasets to public source control without provenance/licensing review. Alternative is an isolated branch-triggered workflow with path guard, but it would no longer be strictly manual-triggered. After input provision, execute and preserve run evidence, compare to corrected archive and record differences. Confirm research source licensing.

**Resource note:** Though concurrency keys do not cancel unrelated Codex jobs, GitHub-hosted runner quotas are shared. Schedule heavyweight replay when available. No impact on Codex source changes or deployment.

**Acceptance pending:** Workflow registration, input artifact, actual execution, output parity and full prospective Career horizon replay. Cap 750/2200 remains provisional.
