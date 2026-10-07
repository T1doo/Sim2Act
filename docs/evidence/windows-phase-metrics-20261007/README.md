# Windows phase metrics: Linux evidence, 2026-10-07

Source baseline: `d51c6781bdb13eb1c8c9c67b4332a3670ef7b025`.
Environment: Linux, Python 3.12.14, existing locked core test virtualenv.
Explicit `PYTHONPATH` selected this checkout's src and tests. PostgreSQL fixture
configuration was unset for the existing-case runs. No real Windows, PostgreSQL,
CI job, external model, LIVE operation or new permission was exercised.

## Results

- [Final plugin selftests](selftests-final.log): 5 passed, 0 failed, 0 skipped,
  2.15 seconds; [JUnit](selftests-final.xml).
- Existing cases, [disabled](baseline-sqlite.log) and [enabled](actual-sqlite.log):
  both 2 passed, 0 failed, 0 skipped, 0.45 seconds. JUnit files:
  [disabled](baseline-sqlite.xml), [enabled](actual-sqlite.xml).
- [Aggregate JSON](actual-sqlite.json): 2 collected, exit 0, COMPLETE, pending SQL 0.
- Ruff: both new Python files passed. Mypy: plugin passed (1 source file).
- Independent reviewer ran the five selftests: 5 passed in 2.17 seconds. Additional
  synthetic checks verified 600 calls across six threads, original argument and
  return identity, KeyboardInterrupt and SQL exception identity, redaction and
  cleanup. Review found no blocker. Those reviewer checks are reported evidence;
  no separate reviewer raw log is included.

The selftests intentionally run a two-case child pytest with one synthetic
failure; baseline and instrumented children both retain exit 1 and 1 failed /
1 passed. The containing five selftests all pass. They also cover inert loading,
output-write failure without secret path disclosure, idempotent initialization,
SQL errors and preservation of subsequent test patches.

## Reproduction

From repository root with the existing environment:

```bash
PYTHONPATH=src:tests python -m pytest -q -p no:cacheprovider tests/test_windows_phase_metrics.py
PYTHONPATH=src:tests python -m pytest -q -p no:cacheprovider -p windows_phase_metrics \
  --windows-metrics-output=/tmp/actual-sqlite.json \
  tests/test_app_previews.py::test_new_input_new_result_and_persisted_history_without_model_or_business_write \
  tests/test_app_previews.py::test_request_key_retry_returns_same_execution_and_changed_input_conflicts
PYTHONPATH=src:tests python docs/evidence/windows-phase-metrics-20261007/overhead.py
```

Remove the plugin and output arguments for the disabled comparison. Recorded
runs additionally used JUnit output paths and unset SIM2ACT_TEST_DATABASE_URL.
The raw logs include the existing Starlette/httpx deprecation warning.

[Benchmark source](overhead.py) and [raw samples](overhead.json) record one warmup
plus six groups, four fresh in-memory Stores per group. Median OFF 0.031675 s,
ON 0.033283 s, observed difference +0.001607 s per group. This includes Store
construction/disposal and is a noisy small warm sample; it is not a Windows,
PostgreSQL, fixture or whole-suite cost estimate. Timings from nested families
must not be summed. Windows 900-second NO_GO remains unchanged.
