# One authorized PG run: initialization timeout; no PG test acceptance

Tested source: `ba5c6d107acdcd42b89a219c49882b113fae5739` (base `7da09fe4d5c0b63c424733eacc82f2eeaca669c8`). [Only CI run](https://github.com/T1doo/Sim2Act/actions/runs/39367188323), attempt 1, job `118446595042`, **failure**. Job ran 2026-10-20 03:59:46–04:03:44 UTC, **238 seconds**, within 15 minutes. No rerun or second marker push occurred.

## Actual result

- Windows Server 2025 x64, 10.0.26100; requested `windows-2025`, actual image `windows-2025-vs2026`, image version `20261007.264.1`, Python 3.12.10. Repository public; standard runner, contents read only.
- Checkout and locked Python dependency installation passed. Initialization reached `C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe ... start`. This path is **not a full measured PostgreSQL version**. No `postgres --version` / SQL `version()` result was captured; full actual version remains unverified.
- `subprocess.run(capture_output=True, timeout=35)` raised `TimeoutExpired` at pg_ctl start, then waited in an unbounded post-kill `communicate()` / Windows stdout reader-thread join. The workflow's 120-second setup cap interrupted it. Logs support a retained output-pipe wait; they do not identify the exact handle holder or establish server readiness / a PG startup failure cause.
- Database creation and restricted app-role creation follow that call and were not reached. Restricted role SQL measurements, schema CRUD grants, per-test isolation receipts, locked DOM install, all **10 selected PG pytest nodes**, and same-cluster restart/cold projection were **NOT_REACHED**. Actual PG pytest executions **0**, passes **0**; restart checks **0**. No JUnit exists. Earlier SQLite passes are not reused as PG results. SQLite-only row-cell barrier remains outside PG scope.
- Actual cleanup and sanitized reporting passed. [`actual/cleanup.json`](actual/cleanup.json) records final pg_ctl status **3** (not running), whole owned cluster/root deleted, private config/initdb password deleted, no container/volume. It does not record pre-cleanup running status or prove whether a stop command was necessary. Do not infer a successful initial server start from this receipt.
- Only one 303-byte cleanup receipt was in the bounded evidence bundle. Its base64/gzip decoded bytes, size and SHA256 match [`actual/manifest.json`](actual/manifest.json). Other setup/test evidence did not exist. Cleanup happened before reporting. Independent pattern scanning found no database credential URLs, Bearer/GitHub/JWT tokens, password assignments or add-mask original values in the archived job log; this is a bounded scan, not proof that all possible secret forms are absent.

## Minimal correction after the failed run

The committed follow-up changes only the PG tool adapter: stdin is DEVNULL; stdout/stderr use random ordinary files inside the same owned temporary root, instead of PIPE. The original 35-second timeout and all role/selection/cleanup gates remain. These files are private transient files removed with the entire root after stop. Returning from pg_ctl no longer requires EOF from its descendants. This directly addresses the observed wait; it is **not a Windows/PG pass**.

[`local-handle-check.json`](local-handle-check.json) records an actual local Linux process adapter check: a wrapper launches a two-second descendant inheriting output and returns in 0.016 seconds; a separate 0.2-second watchdog case returns under one second. Ruff/compile/diff checks passed. No PG was started by these checks. Official context: [Python subprocess](https://docs.python.org/3.12/library/subprocess.html) explains standard-handle inheritance, and [pg_ctl](https://www.postgresql.org/docs/17/app-pg-ctl.html) documents background start, output redirection and status 3.

## Evidence and remaining condition

- [`preflight.md`](preflight.md), [`DESIGN-REVIEW.md`](DESIGN-REVIEW.md), [`design-review.json`](design-review.json): pre-run finite static approval, **superseded for runtime readiness by this failure**. It missed pg_ctl descendant output-handle retention; it does not certify PG success.
- [`ACTUAL-REVIEW.md`](ACTUAL-REVIEW.md), [`actual-review.json`](actual-review.json): independent actual failure/cleanup/log review and finite adapter-patch review; no remaining patch P1/P2, no Windows/PG pass.
- [`run.json`](run.json), [`jobs.json`](jobs.json), [`run.log`](run.log): actual source SHA, platform metadata, step statuses and timeout trace.
- The fixed adapter still needs a newly authorized single Windows/PG run to measure complete actual PG version, restricted app role, ten PG regressions, restart/cold equality, and schema/cluster cleanup. The permission for this run has been consumed; the original marker must never be reused. No automatic rerun is scheduled.
- Original G0/PB limitation and Windows 11 acceptance remain unresolved and outside this run. No PB/G0, real model, paid resource, shared service/account/security change, main change, force push, or deployment.
