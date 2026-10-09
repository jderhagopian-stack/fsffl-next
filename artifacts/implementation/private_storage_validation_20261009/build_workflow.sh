#!/usr/bin/env bash
# Workflow-only build: intentionally NOT invoked by the live FSFFL web service.
set -euo pipefail
DIR=artifacts/implementation/private_storage_validation_20261009
python -m pip install -e '.[web]'
python -m pip install -r "$DIR/requirements-workflow.txt"
python -m compileall -q "$DIR"
python -m pytest -q "$DIR/test_workflow_entry.py"
