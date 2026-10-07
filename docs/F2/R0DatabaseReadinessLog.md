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
