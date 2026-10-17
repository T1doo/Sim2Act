# Independent full CSV report instance-seal review

Reviewed commit: `d2bacd5ccab8ac848956aa637771848ca58404a5`. Base: `44acab540dda5d090eccc21f07d461e2e4462d0c`.

**Conclusion:** the two formally integrated counterexamples independently pass on an exact Git snapshot. No remaining definite blocker was found in the bounded reviewed backend and UI-static scope. This is not a claim that all product, permission or UI regressions passed.

## Actual execution

`tests/test_csv_full_report_instance_seals.py`: **2 passed, 0 failed, 0 errors, 0 skipped**, process RC 0; JUnit 29.027 seconds, wrapper 32.095 seconds. The command, cwd and environment are in `execution-result.json`; raw output and JUnit are unchanged. One Starlette TestClient deprecation warning was emitted; there were no test failures.

The tests exercised actual ASGI endpoints, two isolated SQLite fixtures and original Workers using NoModel. Across the two fixtures there were three distinct successful Runs with one CLAIMED event and fence 1 each, zero model attempts and zero reservations. The first case changed only the Release numeric representation and re-signed its local fingerprint, leaving the independent approval anchor unchanged. Its GET was rejected with 409. The second case first completed an instance-bound report, then jointly re-signed the new adapter copies to another valid but never-adopted Release while retaining the original ordinary contract and instance history. Its GET was rejected with 409. Both rejected reads retained identical fingerprints of all 55 SQL tables. Intentional attack rows remain in the raw fixture databases.

There are 29 raw HTTP receipts, the two `resigned-*.json` results, both `fixture.db` files, and read-only final full-table snapshots. The final database inspection used SQLite URI `mode=ro&immutable=1`, and the whole-file hashes remained unchanged.

## Source and runtime integrity

The snapshot was extracted using `git show` from the reviewed commit, not copied from a changing worktree. All 607 root freeze inputs matched both Git blob IDs and the root SHA256 manifest. Necessary fixed gold/material/evaluation import assets brought the total to 665 Git files. All 665 retained identical SHA256 and Git blob IDs after execution; files were 0444, directories 0555, and there were no extra files in the snapshot. No product or test code was patched, and these tests were not retried. `SIM2ACT_TEST_DATABASE_URL` was removed; PYTHONPATH selected this snapshot's src/tests, bytecode was disabled and third-party pytest plugin autoload was disabled.

The main repository was read only. At final collection, all 100 frozen production Python files still matched d2. The root's current worktree had a three-line pending-UI guard change and an added negative test module. Those later bytes were not executed by these two tests. The explicit bridge hashes and current status are recorded in `final-review-proof.json`.

## Static review

The new adapter reuses the original ordinary CSV prospective prepare, explicit confirmation, three existing tools and whole-report completion. Its Release wrapper reuses existing approvals and immutable Release storage; its adoption wrapper reuses existing switch approval/CAS logic. It creates no executor, Grant or identity, and generic AppRun execution refuses this family. Source/material/artifact authorities remain required before protected bodies. The recipe proof cache is restricted to the current transaction and write epoch, rechecks collected authorities and returns deep copies. Worker terminal typed writes share the original terminal transaction and retain original lease/fence/deadline checks.

The earlier findings are fixed in d2: predictable ordinary-Run and derived-workflow collisions reject; strict accepted UseInput is tied to actual ordinary spec and original workflow request fingerprint; typed results use closed strict schemas and canonical fingerprints; Release snapshots match both independent approval and reconstructed recipe fingerprints; historical bindings map to the exact adopted Release/revision and data-version interval; original instance-creation receipts survive later adoption through original history while returning current pointers separately.

The d2 delivery UI and the root's three-line pending guards were reviewed statically. The controller records identity/connection/workspace/app epochs, per-instance generations and durable per-scope intents. Sending locks are set before the first await, UNKNOWN recovery uses the original GET key, and each write phase requires a separate explicit action. Pending selection now hides/guards the old open button and removes history; detached old callbacks also fail their generation check. No definite scope or duplicate-submit blocker was found in this limited static read. No new JS runtime or native-browser result is claimed.

## Evidence accounting and limits

The first postprocessor followed pytest's `*current` aliases, temporarily listing four paths for the same two physical fixtures. The initial proof and collector are retained; the final proof excludes those symlink parents and reports exactly two fixtures and three unique Runs. A subsequent collector indentation error occurred before database access and was corrected. Neither issue changed product/tests, the pytest result, the oracle, or the fixture database bytes; no test was rerun.

Only these two cases were independently run. Parent-run positives, collision, permission negatives and JS probes must retain their own source hashes and results. PostgreSQL, Windows, real models/semantics, remote CI, old recovery matrices and deployment were not run. The earlier WIP RUNNING observation and old natural/F9 causes remain subject to their original unresolved evidence limits; this passing slice does not establish those causes or remedies.
