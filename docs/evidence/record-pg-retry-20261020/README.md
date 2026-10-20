# Record PG retry: ten tests pass; reporting cap leaves missing originals

PG-tested source: `7f47c74487e794f95ca362b3396b5e0d33a6cd72`, base `5e2775fd921afbb6456f284dc9da1ca7cd9e83b4`. [Retry run 39369709238](https://github.com/T1doo/Sim2Act/actions/runs/39369709238), attempt 1, job `118454583086`: **overall failure**, because report exceeded its compressed payload cap after partially emitting attachments. PG setup, locked tools, all ten PG-compatible record nodes with attached restart hook, and owned-resource cleanup succeeded. This is not a wholly green CI run.

Actual job: 2026-10-20 04:27:59–04:31:32 UTC = **213 seconds**, below its 600-second cap. Previous failed job 238 seconds + retry 213 seconds = **451 seconds** combined, below 900. There were exactly two runs, each attempt 1; no third run. Actual requested label windows-2025, Windows Server 2025 x64 image windows-2025-vs2026 `20261007.264.1`, Python 3.12.10. The public standard runner, loopback-only synthetic cluster, temporary owner and restricted app role scope were unchanged.

## Actual PG execution and role boundaries

Original [JUnit](actual/junit.xml): **10 passed, 0 failures/errors/skips, 80.318 seconds** (console 80.32s). Node names exactly match the ten selected record API/Worker/rollback/fencing/private-scope/page nodes; the explicitly SQLite-only row-cell barrier remains excluded. No model call, PB/G0, live service/account, or readiness negative-security suite was added.

All [ten fixture receipts](actual/fixture-scopes/) name the same temporary app role, record false superuser/create_database/create_role/replication/bypass_rls flags, and confirm their individual schema dropped. Frozen fixture code additionally asserts that role is current_user and cannot CREATE in its schema, using only schema USAGE and table SELECT/INSERT/UPDATE/DELETE for runtime API/Worker/cold pools. Owner is used for the new isolated cluster/database and fixture DDL/grants/teardown. All credentials were temporary, unprinted/uncommitted and removed with the cluster. Secret-shape scanning is bounded; see below.

Same-cluster fast stop/status3/start, changed postmaster start time, existing/cold-pool whole-table equality and authenticated final record projection are inside the attached first-node hook. That node passed; the test driver returns zero only for exactly one completed hook. Frozen source + test-step success + first-node JUnit therefore support one successful hook execution. **The separate restart.json original was not exported**, so the exact before/after timestamps and cold-projection receipt cannot be independently replayed from this archive.

**Complete actual PostgreSQL version string is unavailable.** Setup executed SQL version()/server_version and wrote setup.json, but that original was never emitted before the report cap. The runner image/software list or PGBIN directory is not substituted for the measured SQL value. No value is reconstructed or guessed.

## Actual cleanup

[Exact cleanup receipt](actual/cleanup.json): PASS, final pg_ctl status **3**, whole owned root/cluster/private config/initdb password absent. Its command phase took **0.484 seconds** of the shared 45-second budget. The receipt records initial_status → stop → final_status calls; frozen code enters stop only after initial status 0, requires stop success, then confirms status3 before deleting the root and checking absence. This supports successful actual stop and deletion; the tool's raw status output was not exported. Both test and cleanup workflow steps were successful; cleanup finished before reporting failed. No container/volume was used.

## Partial export, preserved originals and missing evidence

The 2,000,000-byte cap was on cumulative gzip payloads, not total stdout (base64/framing/manifest/RESULT add bytes). The old report streamed paths alphabetically; large pytest UI traces consumed the envelope before setup/restart/test-summary/startup-diagnostic originals. It then failed without a final producer manifest.

Original [run.log](run.log): 2,440,155 bytes, SHA256 `4daa32568eeae1b8f34b770de31e19649a7db099103e25ac650d455054163c03`. Independent readers each decoded **34 complete gzip files**; the 33 non-cleanup originals match cleanup.sanitized_files SHA256 byte for byte. Cleanup itself is preserved from the original log and gzip CRC. The [received index](actual/received-manifest.json) is explicitly a local recovery index, not a nonexistent producer tail manifest. It lists all received sizes/hashes and **19 missing files**. The log retains all emitted compressed files; only bounded core receipts/JUnit are additionally expanded here, avoiding duplication of 8 MB of UI data.

Missing originals include setup.json, restart.json, test-summary.json, run-budget.json, startup-diagnostics.json, test-process-cleanup.json, pytest.log and several later UI/fault artifacts. Their hashes in the cleanup receipt establish names/digests, not contents. They cannot be recovered by the local source fix. Full version value and raw restart receipt remain delivery gaps; raw descendant-cleanup receipt is also missing. Existing test/control-flow evidence is stated separately from missing originals.

[Actual independent review](ACTUAL-REVIEW.md), [structured review](actual-review.json), and [bounded secret scan](bounded-secret-scan.json) agree. The scan found no unresolved credential shapes; twelve Bearer candidates were JavaScript template literals in captured source, and actual headers used synthetic fixture tokens. Deleted random passwords were unavailable for exact comparison, so no universal absence claim is made. The prior failed run's raw evidence remains untouched.

## Local export-only correction after this run

The follow-up report change retains the cleanup/redaction/all-file digest gates and the same 2,000,000-byte gzip payload cap. It plans output before printing, prioritizes core originals and fixture receipts, and rejects core overflow with **zero bundle output**. Optional attachments are included only as whole files; over-budget attachments get explicit `OMITTED_ENVELOPE_LIMIT` entries with original size/SHA256/packed size and zero chunks. The terminal export summary distinguishes `FULL_EXPORT` from `PARTIAL_OPTIONAL_OMISSIONS`. No omission is called complete evidence, and no safety gate or payload cap is loosened.

Final local command: `.venv/bin/pytest -q tests/test_record_pg_ci_diagnostics.py --junitxml=/tmp/record-pg-export-local-final-junit.xml`. **10 local POSIX process/budget/export tests passed**, 3.671 seconds (console 3.67s); [JUnit](export-fix-local-junit.xml), [stdout](export-fix-local-pytest.log). These include the two new core-priority/explicit-omission and core-overflow/zero-output cases. Ruff, compileall and diff checks pass. [Exact export-patch review](EXPORT-FIX-REVIEW.md), [JSON](export-fix-review.json): no remaining patch P1/P2. This local correction was not exercised in Windows/PG, was not used to alter the historic job outcome, and does not restore missing originals.

Only a normal skip-CI development push is used for the correction/evidence. No third run, marker reuse, main change, force push, deployment, new fee, persistent credential, or new security/network permission. Original PB/G0 and Windows 11 acceptance remain outside these record tests.
