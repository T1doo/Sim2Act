P-B cold original-key recovery bridge draft
==========================================

Only this directory was written by the test author. The parent remains the only
writer of `/workspace/Sim2Act`. Adopt the Python file beside the UI author's
`pb_cold_recovery_ui.cjs` under repository `tests/`, then freeze production assets
and both test files before actual execution.

The module fixture builds one fresh ordinary natural-spec source using the
existing `ready` fixture/oracle: three synthetic generation requests and one
normal source `Worker.once()` with one synthetic inference request. Generation
transport is wrapped only for immediate evidence capture; its oracle is reused
unchanged. A second source Run is accepted and cancelled through normal HTTP,
with no Worker or model request, for a genuinely different Run navigation target.
After all owned clients/connections close, `shutil.copy2` seals the SQLite main
file. Each of five page cases receives a physical copy with the same SHA-256;
before any page request, its complete row snapshot must match the seed.

Cases: cold accepted-201 loss and original-key recovery; eight late navigation
boundaries; same-key request/candidate delivery poisoning plus source-read
revocation; target-read revocation; unavailable locks/storage, malformed ticket,
and two cooperating pages. All page scenarios invoke zero Workers. Revocation
uses the real existing Grant API and a fixture-fixed resource/runtime selection.
The denied recovery GET also runs behind the existing SQL private-cell barrier.
Unknown or unavailable platform tests do not invent a new key or send a POST.

The bridge independently verifies one appended app/runtime/extraction marker,
the two existing extractor grants, and only that app's existing sealed journal.
It rejects implicit resources, Release, instances, Runs, attempts or typed data.
After acceptance, all browser HTTP must be GET. Each later checkpoint must keep
all database rows identical except for the one explicitly revoked Grant.

Evidence is flushed through `_PageObserver`: each actual request/response's raw
bytes and hashes, seed rows/source proof/Worker claims and accepted clock,
physical-copy provenance, IPC, browser checks/actions, served asset hashes,
scope-lock events, revocation receipts, SQL barrier statements, source/test-input
hashes before/after, final rows, failures and watchdog status. Its 900-second
watchdog owns only its Node process; the parent supplies a separate outer bound
for this task's pytest process. No old cancelled installation window is invoked.

Completed locally: Python compilation, Ruff, pytest collection (5 cases).
Not executed here: actual product tests, native browser, Windows, real models,
semantic acceptance, PostgreSQL or remote CI. The parent must execute the frozen
adopted pair before treating this draft as acceptance evidence.
