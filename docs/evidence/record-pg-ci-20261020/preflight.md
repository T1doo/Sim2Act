# One authorized record PostgreSQL run: preflight

Base: `7da09fe4d5c0b63c424733eacc82f2eeaca669c8`, on `dev/production-trial-stages-20261018`; target remote equals base. `441fdaa251fd2797857f557a16590946b22756ec` is an ancestor. Main remains `6f688e4dd80b5c81d41aecde90e360d3629f9c21`.

The public repository API returned `private=false`, `visibility=public`, not archived/disabled. GitHub's [standard runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) lists `windows-2025` as free/unlimited for public repositories. Reuse the original Windows-native mock workflow's pinned checkout/setup-python and installed PGBIN. No PG download, container, service registration, artifact storage, paid runner, or repository settings changes.

The explicit user permission covers one run with new random loopback PG port, dedicated RUNNER_TEMP cluster, bootstrap owner and restricted application role/passwords, synthetic data and necessary schema/table grants. Setup uses fresh initdb only; runtime uses NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS, no schema CREATE, and schema USAGE + table SELECT/INSERT/UPDATE/DELETE. Owner is confined to bootstrap/schema teardown. Runtime role and schema checks use actual SQL results. Entire owned directory and private files must be removed before evidence emission.

Original selection: `../record-pg-isolation-20261020/existing-record-regression-nodeids.json`. Exactly ten nodes selected. The eleventh, `test_referenced_json_read_revoke_blocks_current_recovery_and_commit_before_bodies`, is explicitly SQLite-only (`sql_private_barrier.py` rejects non-SQLite). Its prior SQLite evidence is retained; there is no PG privacy-row-barrier claim. No oracle weakening or skip substitution. The first selected node additionally stops/restarts the owned server, checks changed postmaster start time, unchanged whole-table snapshots, and independent authenticated cold projection.

15-minute job cap; test subprocess 300-second watchdog; cleanup/report each bounded. Only exact branch/public repository/attempt 1 plus a unique commit marker triggers the job. The marker is authorized for one push and must never be reused; this is not a durable deduplication service. No rerun is authorized. No PB/G0, PG readiness negative-security suite, or real model.

Local checks before execution:
- Ruff, compileall and git diff --check passed.
- Exact selected ten pytest nodes collected (0 actual PG executions locally).
- Safe temporary-file report checks passed: missing cleanup, missing sanitization, and changed content each withhold all output; sanitized content with matching digests emits a bounded bundle.
- No local PG resource was created and no existing instance was recovered.

One read-only Administration permissions API returned HTTP 403. That endpoint was stopped without retry or settings changes. The ordinary repository/workflow/run reads succeed; no Administration permission is needed or requested for this push-triggered workflow.
