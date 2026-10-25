# App draft directory invalidates on project changes and failed reads

Base9fe3aad52706f9afefd01bb378c9f09a2d1434ec. Related to original V5§2/F2-T05 project-scoped unified entry. An actual template/controller red case showed A's app draft directory remained after selecting B when B's earlier material read failed before refreshApps. This is frontend stale metadata, not a demonstrated backend authorization bypass.

Only app.js production code changes: immediately invalidate app-list on project change; clear/mark unconfirmed during current metadata reads; on current failure expose one explicit read-only refreshApps retry. Identity/connection/project/read generations reject older responses and detached buttons; normal app selection does not invalidate other buttons in the current catalog. Original metadata GET/project filter/family text/showApp/detail/save/execute logic is preserved. Saved-instance use-list and selection controllers are separate, unchanged; this slice does not claim general instance revocation behavior.

red.log preserves original assertion failure. Its shell batch ended with cat; no independent original Node exit metadata is claimed. plan/execution capture4frozen hashes, actual argv, exit/duration and unchanged sources. Three Node processes ran once:

- `NODE_PATH=/workspace/sim2act-research-desk-node-tools-20261023/node_modules node tests/app_directory_scope.cjs`: exit0,7internal checks/6in-memoryGET,0.443341s. Covers immediate invalidation/explicit failure/retry/project filtering/old callback/late response/current buttons. showApp is a dispatch recording stub, not real opening.
- Same NODE_PATH `node tests/goal_directory_scope.cjs`: exit0,11checks/10in-memoryGET,0.414987s. Goal failure/recovery boundaries remain.
- Same NODE_PATH `node tests/resource_directory_scope.cjs`: exit0,15checks/22in-memoryGET,0.415372s. Existing material recovery unaffected.

These are3processes, not33independent tests.0POST/actual HTTP/Worker/model/browser/G0. Node syntax/gitdiff check passed. Independent read-only review confirmed family labels/project filter and all code from showApp onward unchanged, plus source/result hashes. No unrelated backend, provider, permissions or runtime ownership change.

## Previous goal fix: exact evidence and remaining native gap

[Goal repair9fe evidence](../goal-directory-scope-20261026/README.md) contains actual `node tests/goal_directory_scope.cjs` final11checks/exit0, `node tests/resource_directory_scope.cjs`15checks/exit0, and `.venv/bin/python -m pytest -q tests/test_goal_card_run_ui.py::test_goal_history_keeps_current_saved_binding --basetemp=docs/evidence/goal-directory-scope-20261026/pytest-temp --junitxml=docs/evidence/goal-directory-scope-20261026/history-junit.xml`1PASS. These earlier results are bound to9fe, not rerun wholesale or relabelled as native evidence. The new two-directory checks above bind current app.js.

Read-only local browser check found `/usr/bin/chromium`, but its existing `/usr/lib/chromium/chrome-sandbox` is owner65534:65534/mode4755; no local Microsoft Edge path was found. No browser launch retry, install, sandbox change or permission change was attempted. Last protected Edge window was already consumed and bound to another source/state. Minimal missing condition for new pixels is a supported sandbox-valid preview environment, or a fresh exact-source-bound protected Edge read-only run; no such window was started in this slice. New directory failure/retry appearance, actual visible flashback absence, real network/render timing and native interactions remain unverified. DOM success is not pixel acceptance.

Private or real data was not loaded. No server/process started; JSDOM windows closed and all processes exited normally. Existing single-use windows/real model/G0/Windows/device/PG restrictions stay unchanged. No release/main/deployment operation.
