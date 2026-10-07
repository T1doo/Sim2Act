# Task-history Edge wiring delivery

Owned edits: scripts/browser-ci/task-history-ui.cjs (new), scripts/browser-ci/internal-ui.cjs, scripts/windows_browser_ci.py. Other current changes belong to parent and were not edited.

Module shares 39 ordinary task recovery/history user checks with injectable evaluate/reload/normalWorker/snapshot callbacks. Windows helper invokes the module against already running installed Edge, original protected contexts, loopback fixture with existing synthetic-browser-A/B and two new owned projects. Existing internal/agent/protocol flows are preserved. No product API endpoint, activation implementation, model request, bearer user, emit destination, workflow permission or timeout changes.

Normal Mock worker CLI verifies selected owned queued Run before execution and PARTIAL afterwards; no response/status injection. Readonly snapshot returns owned Run IDs, Attempt mode/status, Operation status and global grants/principal counts, without goals/request keys/credentials. Module requires7acceptedRuns,2RECEIVEDMOCKAttempts,VERIFIEDoperation and unchanged grants/principal counts.

Final desktop/mobile output slots show7new history rows and the restored original Partial task canvas. Prior internal UI layout checks remain, and prior historical PNG evidence is not changed. Pixel review remains NOT_REVIEWED. Protected actual Edge before/after asserts observed argument policy, no disabled features, actual restricted low-integrity/AppContainer renderers via original Windows read-only token audit.

Offline v2 invocation:
NODE_PATH=/workspace/browser-tools/node_modules PYTHONPATH=src /workspace/sim2act-pb-venv/bin/python /tmp/task_history_module_offline.py /tmp/sim2act-task-history-module-offline-v2

Results:39PASS,7acceptedRuns,2normalMOCKAttempts,1VERIFIEDreceipt,grants4->4,principals6->6. Module-results at /tmp/sim2act-task-history-module-offline-v2/module-results.json. Node harness /tmp/task_history_module_offline.cjs and Python harness /tmp/task_history_module_offline.py use real local HTTP/JSDOM/syntheticSQLite; they import only fixture readonlysnapshot function and never invoke/pretend Windows protected main. Local syntax/Ruff/py_compile/diffcheck PASS. Native Edge execution and pixels NOT_RUN here due actual platform gate; parent owns PG/fullsuite/push/CI.
