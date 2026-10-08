# Complete Engineering PostgreSQL phase evidence

See [result and remaining gates](../../F2/EngineeringPGPhaseLog.md) and
[reconstructed plan](../../F2/EngineeringPGPhasePlan.md).

- `first/`: actual complete baseline run on
  `5c06520bc31269d11b9bf2786b9e18ed89333a28`;1586 collected,
  1552 passed/7 failed/27 skipped. Collection, JUnit, phase reports, existing
  aggregate metrics, source snapshots, dependency and stage receipts are retained.
  `first/controller.py` and `first/engineering_phase_audit.py` are exact executed
  diagnostic sources; their hashes are in first-instrumentation-sha256.json.
- `postfix-pg-start-failed/`: actual candidate startup failure on
  `2315fea1f803ca45e0cbd5ff3da6a329a40d1a1d`; no collection/test/JUnit. This
  folder also retains the earlier short-SHA rejection before resource creation.
- `focused/`: preflight13PASS; initial dependency-path omission100PASS5FAIL and
  corrected original five-module SQLite105PASS0FAIL0SKIP; current Ruff/mypy47.
- `independent-review/`: four independent reviews of frozen runtime source
  `f9044237805e91438807d5acbf9b963ac8af83e4`; additional preflight13PASS and
  deterministic SQLite lease2PASS, exact raw review reports/commands/JUnit/logs,
  retained Docker events and SHA256 manifest. No PG/full rerun. Historical startup
  root cause is unresolved; the explicit restart condition is not met.
- `assertion-preservation.json`: all137 original assertion ASTs in modified
  tests are preserved. `postfix-source-current-equality.json` verifies283 source
  files against candidate preparation bytes, without inventing a SQLite
  before/after snapshot.
- `owned-docker-events.json`, `owned-volume-cleanup.json`, `fixture-cleanup.json`:
  exact ownership and cleanup evidence. Driver logs preserve the protected
  Chromium startup skip. No source/claim from the original instance was recovered.

Recompute first-run analysis from safe exported data:

```bash
.venv/bin/python docs/evidence/engineering-pg-phase-20261008/analyze.py \
  docs/evidence/engineering-pg-phase-20261008/first
```

This read-only command does not start a database or tests. Live controller
execution requires a separately allowed owned PG run; its updated TCP readiness,
per-definition fixture ledger, log/mount capture and anonymous-volume cleanup
are statically reviewed, not newly runtime-PG validated. No test/timeout/security
gate was relaxed. Export manifests contain raw/export hashes and URL-redaction
counts; originals remain in this run's /tmp log roots after fixture deletion.
The installed venv and owned Node dependencies remain in the new instance.
