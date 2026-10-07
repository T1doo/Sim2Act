# R0 database readiness draft: limited local verification

Independent branch dev/r0-db-readiness-local at /workspace/Sim2Act-r0-db-readiness; base cb3d600a58bb6cba9cb97b6c64ebad4772251451. Plan5859396 precedes source b701c751d2429a1177916662419b9cd0e35d55f4. Root final/full source and other trees were not modified; no merge/push/CI/full was run.

New db_readiness inspects only fixed pg_catalog SELECTs (six on the healthy path). Current40 metadata relations, declared columns/types/nullability/type modifiers, primary/unique keys, effective schema/name resolution, schema USAGE, each CRUD privilege, current/session/reachable admin/owner roles and schema CREATE are checked. Unsupported dialect/schema/catalog/type shapes fail closed. PostgreSQL system functions/relations are explicitly qualified; no business rows, pg_authid passwords, DSN/token/raw exceptions are returned. There is no DDL/DML, migration, repair, identity/Grant change, Start or provider work.

Doctor calls the module and emits closed JSON/nonzero BLOCKED. database=UP retains its connection-only meaning and existing Windows smoke mode field remains; status must separately be STRUCTURAL_READY. Doctor no longer needs processes.json just to inspect the DB. Start/Status/Stop are otherwise unchanged. STRUCTURAL_READY is a catalog diagnosis read at that time, never a later authorization receipt or proof of RLS/triggers/business writes/identity/worker/browser/Win11/R0. Product operations retain their original current authorization checks.

Frozen source commands:

- `PYTHONPATH=src /tmp/sim2act-delivery-adapter-venv/bin/python -m pytest -q tests/test_db_readiness.py tests/test_process_identity.py --junitxml=/tmp/r0-db-readiness-draft/final-unit.xml`:41 unique PASS,0 SKIP,0 FAIL,0.50s (35 new synthetic catalog/Doctor +6 existing pure process-identity guards).
- Ruff module/manage/newtests:PASS.
- mypy new module:1 file PASS; mypy src:42 files PASS.
- Additional mypy module+manage:2 FAIL in manage. Parent cb3 manage independently has exactly the same2 issues (status dict→string assignment, Windows constant absent from Linux stub). Both logs preserved; no static suppression or unrelated lifecycle change. This extra script check is not reported PASS.

Tests exercise reachable/empty/old/damaged/shadowed catalogs, missing individual CRUD, current/session-reachable owner/admin flags, schema CREATE/USAGE, unavailable catalog/role/type/dialect, credential sentinel suppression, safe CLI exit and invalid process state ignored by Doctor. Synthetic positive data is not evidence that actual PostgreSQL catalog functions, driver type decoding or membership behavior work. No real PostgreSQL connection/role provisioning was performed. SQLite engine is only rejected as unsupported; it does not qualify PG.

Evidence: docs/evidence/r0-database-readiness-draft-20261007/validation.json, source/artifact hashes, actual41-case JUnit, unit/static/baseline/development logs. All local sessions naturally ended; no live API/worker/DB process was started or owned. Remaining: root-authorized own-label PostgreSQL role oracle after final full cleanup; actual powerShell/Win11 clean-user walkthrough; independent review and separately authorized integration. This isolated draft is not part of the frozen root candidate and does not raise R0 or formal-publication status.

## Independent b701 BLOCK and corrected source

Original independent static report SHA6b620c78ccf9c1f58d8f8743f7b0f76547fc63fdb7fa380ac7016e4621602a65 identifies b701 safe-output disposal and reachable schemaCREATE blockers. It is copied unchanged as correction-1bf2481/original-b701-BLOCK.json; earlier41PASS did not cover these and is not rewritten as full acceptance. Correction Plan97d8977 precedes source1bf24811c9e60718b33fc41f9433bab83856232c. Doctor dispose exceptions now append ENGINE_CLEANUP_FAILED/BLOCKED/NOT_ESTABLISHED and still emit safe JSON/exit1. ROLES adds strictbool schema_create_reachable across its existing current/session/MEMBER set. Source preserves conservative membership scope.

Necessary corrected unit run retained all41 and adds3:44 unique PASS0.44s/JUnit, RuffPASS, src42mypyPASS. No PG or Docker was run. Independent exact1bf static correction report SHA425695292c3c9135ae61168c451dfd08d574ceae5315b2c2defd42b667ebcfc0 copied unchanged; STATIC_CORRECTION_PASS is not actual PG membership/call/driver validation. Prepared23-case realPG matrix and fixture source are in R0DatabaseReadinessPGOraclePlan.md/tests/test_db_readiness_pg_oracle.py, deliberately not collected/executed. It waits for root GO/full owned cleanup0, then one owner handles exact label/loopback/private config/container lifecycle; no root/full DB reuse.

## Ordinary-only correction freeze

Scope Plan9bf5c6b precedes checker4591e91d7c2caf1c27411c236df73fc0bb99ea43. Only relation r qualifies; p is unsupported SCHEMA_MISMATCH. Actual original44 plus partition negative:45PASS0.58s,45 JUnit cases; whole-src mypy42PASS. First Ruff failed unused copy in unexecuted PG driver; removed unused import and final RuffPASS. Prior b701 BLOCK and1bf static correction evidence remain byte-identical. Evidence: ordinary-4591e91/validation.json and hashes. PG23 prepared only (not collected/executed); token now binds corrected4591 source. No Docker/PG started. Existing script-only mypy2 baseline failures remain; readiness remains catalog-only, R0 NOT_ACCEPTED.
