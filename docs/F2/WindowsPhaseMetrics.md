# Optional pytest phase metrics

This diagnostic slice measures fixture setup, `Store.initialize`, table existence
checks and SQL cursor execution before deciding whether database initialization
is worth optimizing. It does not change the Windows 900-second NO_GO assessment.
Baseline: `d51c6781bdb13eb1c8c9c67b4332a3670ef7b025` (`dev/f1-foundation`).

## Explicit activation

Use the existing test environment and retain the original test selection and
pytest options. Add this plugin and an output file in an existing directory:

```bash
PYTHONPATH=tests:src python -m pytest -p windows_phase_metrics \
  --windows-metrics-output=/tmp/windows-phase-metrics.json
```

Equivalent PowerShell invocation from the repository root (not verified on
Windows; use the project's existing Python environment):

```powershell
$env:PYTHONPATH = "tests;src"
python -m pytest -p windows_phase_metrics --windows-metrics-output=windows-phase-metrics.json
```

Both explicit plugin loading and the output option are needed for measurement.
Loading the plugin without the output option leaves instrumentation inactive.
There is no automatic conftest registration or CI integration. The plugin does
not select, skip or deselect tests. Its five independent tests are new repository
tests; activation does not alter collection on the same checkout.

## Reading the JSON

- `collected_cases` and `pytest_exitstatus` describe this pytest session.
- `fixture_setup` counts actual setup invocations, including failed setup, not
  fixture requests or teardown. Cached fixture requests are not new setups.
- `initialize` measures the whole original method; `has_table` measures the
  original SQLite/PostgreSQL dialect method. Labels are fixed fixture names
  (`env`, `runtime_role`, `browser_seed`, `registered_browser_fixture`),
  `outside_fixture`, or `other`. Custom names, IDs and parameters are omitted.
- `sql` separates initialization from other execution and groups cursor duration
  by fixed dialect/operation labels. `existence` means execution inside
  `has_table`; a dialect may issue multiple statements per method call. DDL is
  classified using SQLAlchemy's execution context.
- `seconds` is accumulated duration; `max_seconds` is the largest observation.
  Nested and concurrent observations overlap: do not sum families to obtain
  wall time. Cursor duration excludes fetch, commit, and connection acquisition.
- `COMPLETE` means no pending SQL event remained at session finish. It does not
  establish coverage of subprocesses, teardown, browser timing or the CI job.
  An interrupted process may produce no file. Unavailable or incomplete metrics
  cannot support a budget verdict.

Temporary wrappers forward the original arguments, return values and exceptions;
SQL listeners do not replace errors. Cleanup removes listeners and restores
wrappers unless another test/plugin has replaced them. No schema, transaction,
database permission, provider, product code, main conftest or workflow is changed.
Output contains aggregate timings and fixed labels only: no SQL text, parameters,
DSN, environment values, exception messages or test/fixture IDs. A failed output
write reports only the exception class and preserves the pytest test outcome.
No software installation, login, security setting change or external model call
is performed.

## Verified Linux example and limits

Evidence: [2026-10-07 measurements](../evidence/windows-phase-metrics-20261007/README.md).
The two existing CSV preview/history and retry/conflict cases passed both with
and without instrumentation (2 collected, 2 passed, 0 skipped, each reported
0.45 seconds). The measured run recorded 2 `env` setups, 2 initializations,
80 `has_table` calls, 80 DDL cursor executions and 160 existence cursor executions.
Initializer total was 0.029767 seconds; existence-method total 0.004576 seconds;
DDL cursor total 0.008744 seconds. These observations overlap.

A small warm SQLite benchmark alternated OFF/ON/ON/OFF/OFF/ON, four new in-memory
Stores per group. Median group duration was 0.031675 seconds without observation
and 0.033283 with observation: +0.001607 seconds per four Stores (about 0.402 ms
each). Each sample includes construction, initialization and disposal. Three
samples per mode do not establish a stable full-suite overhead or a performance
threshold. No Windows or PostgreSQL execution was performed.

Mainline may cherry-pick this slice and add the CLI options to a diagnostic run
while keeping its original cases, assertions and guards. Full Windows evidence
must still measure the same qualified job, PostgreSQL fixture count/cost, browser
completion and cleanup. This slice neither enables `checkfirst=False` nor permits
test/browser overlap, extra privileges, or a CI budget change.

## Subsequent mainline PG classification (2026-10-07)

Integrated opt-in plugin b89dd986 by normal merge1c45795a06bc4f2e2d2210540520470582f64c72 after NL82 source freeze; only two new test/plugin source files, no core/conftest/workflow change. Merge self-tests5 PASS/3.00s and whole Ruff/mypy44 PASS. [Exact PG measurement](../evidence/windows-phase-metrics-pg-20261007/README.md) preserves257 source hashes and original two CSV cases: OFF2 PASS/2.487s and ON2 PASS/2.528s, no skips/retries. ON COMPLETE/pendingSQL0. Fresh synthetic PG from an existing local image; owner fixtures retain explicit schema/migration initialization and original assertions.

Two initialize spans224.882ms within two env setups665.858ms (33.77%);80 has_table calls59.573ms (26.49% of initialize),80 existence cursor spans43.395ms,80 DDL spans115.889ms. Method and cursor spans overlap and omit different costs; do not sum them. OFF/ON wall delta40.783ms is one pair, not stable instrumentation overhead or causality. All owned schemas/extra roles/public tables/controllers/container cleared. Raw SHA and sanitized SHA were recorded (this export changed no bytes); a duplicate private-file unlink error in finalizer is separately retained and remaining cleanup completed without rerunning tests.

Optimization decision: this small Linux sample identifies initialization as a measurable fixture component, but gives no full-job initialization count, Windows cost, absolute savings or coverage qualification for a behavior change. No fixture reuse/cache/checkfirst=False or overlapping test/browser execution was implemented. The next optimization must preserve fresh ownership and all original assertions, and obtain representative same-capacity counts and before/after evidence before claiming budget savings. Windows900/Edge240/Node150 remain unchanged NO_GO; no new CI. This PG sample does not qualify NL planning, production activation, semantic acceptance or R0.

Independent measurement review LIMITED_PASS: all16 original exports,257 Git-bound source files and both actual per-node JUnits verified; ratios recomputed. Cleanup verified against owner receipts and local path absence, without independent Docker/PG census. Raw originals deleted after exporter recorded hashes; review rehashes safe exports and does not claim a new raw byte inspection. See independent-review.json in the PG evidence directory.
