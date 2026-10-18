# Original P-A page test observer draft

This directory is isolated. The agent did not write `/workspace/Sim2Act`, Git, old evidence, or any CJS file, and did not execute the WIP page scenario.

Deliverable: `pa-page-observer.patch` changes only `tests/test_pa_natural_spec_ui.py`; the complete proposed file is under `tests/`. SHA-256: `e142628a9873f4614827e1cbf71b2d0c959e0ef4146369375b586362b08cd07a`. The baseline copy has SHA-256 `13663a3d8f390e6101608a89a12e381947a8038f987e0d64655de40925c329c4`.

`py_compile` and Ruff passed. `assertion-invariance.json` records actual AST comparison: all 10 original Python assertions, the complete original synthetic provider handler, both Worker constructors, and the MockTransport constructor are unchanged. The original CJS SHA-256 remains `83e2ea72fff1461eb8bc6fc142265aa70842c77eb60fda299fdc2db04a5e3242`; no original CJS gesture/check, 15-second bounded wait, or 3+2 MockTransport request assertion was changed.

Each new test run writes its own evidence directory:

- `progress.jsonl`: each Node stdout line, RPC start/end/error, HTTP start/end/error, Worker start/end/error, response saved, model request appended, owned Node start/exit/kill, and test finalization. Every event is flushed immediately and has a sequence, UTC time and monotonic elapsed time.
- `http/*-response.body`: exact original HTTP response bytes. Companion metadata records method/path/body, response status/content type/byte length/SHA-256 and the RPC ID.
- `model-wire.jsonl`, `runtime-wire.jsonl`: each original list append, flushed immediately. The original list behavior and handler/transport calls remain unchanged. `model-wire.json` and `runtime-wire.json` are also checkpointed and written in finalization.
- `driver.log`: Node stderr is directed to this owned regular file, avoiding the original unread stderr pipe. The existing return-code assertion still uses the resulting complete error text after Node exits.
- `errors.json`, `progress-summary.json`: written in finalization on normal completion or Python exception unwinding. Errors include full Python tracebacks; Node stderr remains intact in `driver.log`.

A 900-second timer calls `kill()` only on this test's exact owned `Popen` Node object. No PID scan, process-group kill, lock removal, unknown process action, CJS change, or permission change was introduced. The existing CJS and durable-browser helper do not spawn another process. The inner timer cannot interrupt a synchronous Python HTTP or Worker call, so root's separately authorized outer owned 900-second test bound remains required. Hard termination of Python cannot execute its finalizer; the flushed incremental files are the preserved evidence for that case.

This improves future observability only. It does not qualify any old NOT_VERIFIED full-page run or recreate the old missing/full-disk evidence.
