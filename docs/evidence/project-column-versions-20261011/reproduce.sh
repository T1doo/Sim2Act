#!/usr/bin/env bash
# SQLite/real worker/in-process HTTP/offline JSDOM only.
set -eu
NODE_PATH=${NODE_PATH:-/workspace/node-tools/node_modules} .venv/bin/python -m pytest \
  tests/test_project_column_versions.py tests/test_project_column_versions_ui.py \
  tests/test_project_column_patches.py tests/test_project_column_patches_ui.py \
  tests/test_column_patches.py tests/test_column_patch_keys.py tests/test_column_patch_controls.py \
  tests/test_delivery_graph.py tests/test_delivery_graph_apps.py \
  tests/test_delivery_graph_receipt_types.py tests/test_delivery_graph_source_version_types.py \
  tests/test_manual_locks.py tests/test_project_revalidation.py tests/test_report_presentations.py \
  tests/test_csv_dag.py tests/test_csv_dag_boundaries.py tests/test_csv_dag_proof_guards.py \
  tests/test_csv_two_sum_instances.py tests/test_csv_dag_instances.py \
  tests/test_csv_report_dag_instances.py tests/test_csv_dag_version_switch.py \
  tests/test_internal_lifecycle.py tests/test_internal_api.py \
  -k 'not actual_previous_dev_source_upgrade and not actual_f13_upgrade' \
  -q --disable-warnings --basetemp=/tmp/project-column-versions-reproduce \
  --junitxml=/tmp/project-column-versions-reproduce.xml
