# Linux full regression convergence — 42b7a99

Frozen source: `42b7a992524d9f2e00136711c70cb4e16f3e419b`.
This evidence branch changes documentation only. Product implementation remains
`67807be6940cda16007a6a0cca90d9b04a589461`.

## Scope and method

The original default `tests/` selection contains 2051 unique tests across 127
tracked modules. Both backends independently collect exactly that selection,
then run it sequentially without xdist or concurrent duplicate tests. This is
new evidence for this source; historical 1591-test results are not reused.
Original assertions, source, schemas, scripts, workflows and dependency locks
are SHA-256 compared to the frozen Git tree before and after each run.

`LIVE=0`, `SIM2ACT_LIVE_ENABLED=false`; no real model, new CI, deployment,
credential configuration or security privilege changes. PostgreSQL uses this
task's private container, network=none, no ports, a private Unix socket, and
only isolated fixtures. Browser dependencies and upgrade archives are private
temporary resources. Original old/core upgrade tests are included.

## Results

| Backend | Collected / executed | PASS | SKIP | FAIL | Seconds |
|---|---:|---:|---:|---:|---:|
| SQLite | 2051 / 2051 | 1954 | 97 | 0 | 1528.84 |
| PostgreSQL | 2051 / 2051 | 2021 | 28 | 2 | 2836.28 |

PostgreSQL first round is FAIL, not a clean baseline. Its two failures are
`test_natural_goal_actual_http_ui[valid]` (missing acknowledgement after reread)
and `test_pg_resources_graph_share_project_first_lock[resources-history]`
(original Future.result timeout=10). The latter retained actual project-first
blocking, no SQL error/deadlock, but timed out before collecting response status;
this is not sufficient to declare resource interference or a product lock bug.
Both original page aggregate tests PASS, with all 16 DOM checks each.
First-round evidence stays immutable; candidate follow-up results are separate.

See `sqlite-summary.json` and `pg-summary.json` for exact first-round counts,
elapsed times, return codes and provenance. `*-first.log/xml` retain complete
first-round output. `*-problems.json` and `*-skip-reasons.json` preserve skipped
node identities, reasons and details. `*-actual-proofs/` retain actual original
page, Node and browser driver evidence; no skipped browser launch is PASS.

Static checks: `ruff check src scripts tests` PASS; `mypy src` PASS (52 files);
all product JavaScript passes `node --check`. These completed before full runs.
Original page aggregate `tests/test_product_integration.py` is in the full
selection. The exact Node/JSDOM/Playwright versions are in
`node-dependencies.json`; Node timeouts retain the original 150-second bound.

Windows 900 / actual Edge 240 / Node 150 standards remain unchanged. Linux
full-suite elapsed time is reported without substituting it for a Windows
result. Actual Win11 ordinary-user native install/start/stop/restart and Edge
are NOT_RUN. Linux Chromium's protected sandbox cannot start in this environment;
its original skipped-test reasons and driver stderr are retained, with no
sandbox bypass or privilege adjustment. Private-oracle/R0 tests remain skipped
unless their original explicit gates are satisfied.

## Reproduction and cleanup

`run_full.py` is the exact first-round runner. It refuses to overwrite existing
summary files, verifies the frozen source and selection, and preserves actual
proofs. Reproduce in a fresh checkout/evidence directory with Python 3.12,
repository dependencies, Node v24.19.0, jsdom 30.1.2, playwright-core 1.63.0,
and the original upgrade archives at the paths in the runner environment.

SQLite: unset `SIM2ACT_TEST_DATABASE_URL` and run
`LIVE=0 SIM2ACT_LIVE_ENABLED=false NODE_PATH=<private node_modules>
SIM2ACT_UPGRADE_OLD_ARCHIVE=<old archive> SIM2ACT_UPGRADE_CORE_ARCHIVE=<core archive>
.venv/bin/python docs/evidence/linux-convergence-42b7a99-20261008/run_full.py sqlite`.

PostgreSQL: supply an explicitly owned isolated test URL, then the same command
with backend `pg`. This task uses PostgreSQL 17.9 with image/container identity
recorded in `cleanup.json`. Never point these full fixture tests at shared data.
After both test processes terminate, `cleanup.py` checks no test schemas,
temporary roles or public tables remain, then removes only this task's
container/image and temporary dependency/archive/fixture paths. Final cleanup
and remote ancestor/change verification are recorded separately.

[F2 status and next implementation](F2-status.md) maps the original V5 contract
without claiming general P-A/P-B, human acceptance or formal release. The
highest-value product follow-up is a narrowly defined existing non-CSV change
with actual new output/checks and authorized PROJECT job completion; target
Windows acceptance remains a separate prerequisite.
