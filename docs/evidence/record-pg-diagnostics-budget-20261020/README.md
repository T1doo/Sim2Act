# Bounded startup diagnostics and shared cleanup command budget

Base: `4d8e2076c32bb82c42f8eaaf7b61767905de64f1`, development branch `dev/production-trial-stages-20261018`. This follow-up addresses two concrete defects found after [the one failed PG run](../record-pg-ci-20261020/README.md); it does not certify PG startup or add a CI run. The parent explicitly requested local fixes/review/testing and a skip-CI normal push while it checks the existing authorization scope.

## Changes

`tool()` now reads and archives already-written output when a subprocess times out, before raising the generic watchdog error. The first tool failure diagnostic survives later cleanup. Cleanup always snapshots startup logs before deleting the owned directory, including when a command fails. Diagnostics allow only `postgres.log` and exact `tool-<32 lowercase hex>.stdout` / `.stderr` names in the owned root. The collector does not open private.json or password files; config() still reads its required control configuration separately. Symlinks, Windows reparse points, nonregular files and multiple-hardlink files are rejected.

Diagnostic collection scans at most 64 directory entries, reads at most eight files, at most 4,097 bytes each (32,776 bytes total), and writes at most 262,144 UTF-8 JSON bytes. Only complete newline-terminated lines are retained; cut/unterminated final lines are dropped with explicit metadata. Known owner/app passwords and URLs are replaced before export; PostgreSQL URI forms and long hex tokens are additionally masked. No raw arguments, private-file content, password or connection string is copied to diagnostics. Sanitized files remain subject to the existing cleanup/redaction/digest report gate. The ordinary-file approach from 4d8e207 remains: descendant EOF is never required.

Cleanup process termination and all status/stop/status calls share one monotonic **45-second command deadline**. Status calls have at most five seconds; stop remains at most the original 35 seconds and reserves five seconds for final status. Its positive pg_ctl `-t` is shorter than its subprocess timeout. Remaining time is checked again after output files are opened. Exhaustion starts no further command, triggers no retry, and does not delete a cluster without final status 3 or write PASS. The existing workflow's **60-second cleanup step** and **15-minute job** stay unchanged; 15 seconds remain outside the command budget for bounded diagnostic archival and filesystem deletion. Filesystem calls have no independent cancellation mechanism; the unchanged outer 60-second step is their hard cap, and failures cannot produce a successful cleanup receipt.

Official references checked: Python documents [Windows reparse attribute flags](https://docs.python.org/3.12/library/stat.html); PostgreSQL documents [pg_ctl waiting, timeout and status behavior](https://www.postgresql.org/docs/17/app-pg-ctl.html). A pg_ctl timeout alone cannot prove whether the background operation later succeeded.

Independent final [review](REVIEW.md), with [structured findings](review.json), matches the frozen runner/test hashes and has no remaining P1/P2. It verifies the local evidence only, and makes no Windows/PG acceptance claim.

## Actual local verification

Command: `.venv/bin/pytest -q tests/test_record_pg_ci_diagnostics.py --junitxml=/tmp/record-pg-diagnostic-local-junit-v2.xml`

Result: **6 passed**, 0 failed/skipped, 3.41 seconds; original [JUnit](junit.xml) and [pytest stdout/stderr](pytest.log) record 3.408 seconds. These are local Linux Python executable shims, not Windows or PostgreSQL emulation. The fake PG-named script only sleeps, records calls, and returns synthetic exit codes; it never invokes PG, opens a network port, or creates database resources. The expired-clock boundary case explicitly advances only the harness's clock; the other timeout/process cases use real local processes.

Coverage:
- Timeout stdout/stderr are saved, credentials removed, unterminated secret prefix dropped; diagnostics survive owned-root deletion, and credential files are never collector inputs.
- Large/truncated and unterminated logs, file/read/JSON caps, symlink/hardlink rejection, unregistered URI and uppercase hex masking.
- Three real local status/stop/status processes share the same deadline, with a final-status reservation.
- A nine-second synthetic stop is killed by the remaining shared budget (test completed in 2.603 seconds), with diagnostics retained and no deletion/PASS without final status.
- At an exhausted shared deadline, no final-status process starts; diagnostics remain and root is preserved.
- Missing PG_VERSION is not treated as proof of no running cluster: diagnostics remain, no PG command starts, root is preserved and PASS is withheld. This closes the P2 found during independent review; the final six-node local test run includes it.

Ruff, compileall and git diff --check passed. No product, role, test selection, workflow gate or timing limit changed. Actual PG executions in this follow-up: **0**; new CI runs: **0**. Full Windows/PG version, restricted-role measurements, ten PG cases and restart remain unverified.

## Original evidence preserved

- Previous raw run.log: SHA256 `4324db64a8b67e2ff612c40b237ee4d823e5283cfaf99eb5afdafc8d1f05e67d`.
- Previous exact cleanup receipt: SHA256 `8f14a0d16b315eeae4636a8abee5e413487c48c27e31b3d2a0ff8995ac94bd34`.

Both original files remain unchanged, including Git blob bytes. No new authorization conclusion is made here; this task specifically defers any next PG CI to the parent.
