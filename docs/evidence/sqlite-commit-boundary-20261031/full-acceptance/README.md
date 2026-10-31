# Frozen default-path save, reopen and cancellation acceptance

Application source: `bbe2a11c86648bc9a57a5e457418c30149c95cf7`, including cancellation recovery `e7b0916b12e7459fed5c90f5502dde5d7c148420`. The recorded source and Git status stayed exact and clean throughout execution. No application source was changed for this archival commit.

Real-clock Linux, original large synthetic Cold fixture, local test SQLite, FixedMock. Started 2026-10-31 15:33:17 UTC; completed 15:47:35 UTC. Save and cancel pytest commands each exited 0; first fresh-process reopen and default recovery each exited 0. No other measurement ran concurrently. This is a later functional acceptance, not an adjacent randomized performance comparison or evidence that the commit-boundary fix caused a speedup. See the exact commands/timestamps in `cold-lifecycle-bbe2a11c-20261031-acceptance.json`.

| Actual transaction | G0 read (s) | Writer scope (s) | Total (s) | Outcome |
| --- | ---: | ---: | ---: | --- |
| First Cold | 29.406537 | 44.285788 | 73.693055 | COMMITTED |
| Second Cold | 31.338714 | 45.970290 | 77.309448 | COMMITTED |
| Cancellation during actual G1 writer | 32.398843 | 4.700587 | 37.100211 | ROLLED_BACK |

G0 and writer are disjoint observer scopes; total also contains small transition overhead. Writer scope begins immediately before the first DML, in before_cursor_execute, and includes acquisition/cleanup; it is not an isolated fsync, exact SQLite lock-hold, or G1-only timer. The independent SQLITE_BUSY probe below establishes an actually held writer during G1. **G0 is not stably below 30 seconds and the 44–46-second writer remains a performance limitation.** The unchanged signed 120-second received-attempt settlement interval spans G0 and writer, whereas the original 30-second claim/admission/first-DML condition is a distinct contract; these figures do not redefine either condition or prove the original 30-second whole-validation goal.

## Save and first fresh-process reopen

Both Cold attempts are VERIFIED and the Run is SUCCEEDED. The first new Python interpreter, before any database archival/probe, confirmed one result/instance version, seven attempts and equality of saved HTTP output, AppRun output and typed result. Main database SHA256 `744367deb9e3f6d2ea632b897442212f426377b09d1a70415938bf8f1f60fc23`; logical content SHA256 `173f926b212082ec12aa23b27a4859e75bdd901ea48a74a81e8f014c30355573`. Opening read-only SQLite changed absent WAL to an empty WAL; physical file-set identity is explicitly false, logical content and main bytes are unchanged. Nonempty WAL frames would require exact identity. See `save-first-reopen.json` and its command record.

## Actual held-writer cancellation and default convergence

A second connection received SQLITE_BUSY (5) during the actual G1 writer, proving the test reached a held SQLite writer. Status GET returned 200 in 0.165925 s; cancellation POST returned 200 in 0.234831 s with RECONCILING. The interrupted transaction rolled back: original prior attempts, received response, archived evidence, resource rows and typed history remained unchanged, with no settlement/rejection prematurely written. This original rollback database is preserved separately as `cancel-fixture.db.gz`.

The helper copied that exact database to a separate recovery directory, then invoked the normal default `Worker.once()` in a fresh interpreter with model requests forbidden. One iteration reconciled the known received receipt to REJECTED_KNOWN and Run/AppRun to CANCELLED; version 3→4 and fence 1→2. Original response/usage, ledger, archives, reservations, resources and typed history remain unchanged. Two repeated public cancel requests returned 200 without incrementing version. Another Store/default-worker open and another fresh Python interpreter performed no replay and observed CANCELLED. Control-progress returned 200/CANCELLED. The original cancellation input database stayed byte-identical: SHA256 `8efd79fc2a45c385670e636d8c2f5da6873ba193dcada6463df5fb62939a79cf`.

**Lease-label clarification:** the raw helper/step/file names retain “natural-expiry” and its original classification. Actual `started_lease_until` is **0.0**: the original worker normally released its lease after rollback. No test edited the lease or clocks, but this run did not wait for a future 120-second deadline to elapse. `lease-end-interpretation.json` records this distinction without rewriting original evidence. The helper's 1.312113-second wait/check/recovery measurement includes API and fresh-process checks and is not an isolated worker-response latency. Still-live-owner refusal is covered by the separate targeted negative regression, not by this large sample.

## Scope, review and retained failures

There were 7 FixedMock requests in save, 6 in the cancelled workflow and 0 in recovery: **13 FixedMock / 0 real provider calls**. No production PostgreSQL, new Windows build/runtime or real-model semantic acceptance is claimed. Current configured INTERN token readiness was observed without printing its value; this test uses no token. No main, Release, new CI, PC, credentials, permissions or fees were involved.

The final pre-freeze targeted regression is 141 PASS / 0 skips, independently source-reviewed, with original receipt, callback, revocation, alias, concurrency, finite-clock and rollback counterexamples retained. This is not a claim that the entire repository test suite is green: the separately recorded 58 continuation failures include 16 historical fixture-schema and 42 reviewed-software-target refusals, reproduced against the original baseline and retained under [cancellation recovery evidence](../../cold-cancel-recovery-20261031/README.md). No production qualification/type gate was relaxed to pass them.

All archived database contents derive solely from synthetic pytest materials. The archival scan checked configured secret exact values in the source bytes without printing them; manifest hashes bind both compressed artifacts and original bytes. Original rollback and recovered databases are separate artifacts.

Current runtime readiness was checked on 2026-10-31: `INTERN_API_TOKEN` ready/nonempty, dedicated override absent; no `SIM2ACT_DATABASE_URL`, `DATABASE_URL`, `PGHOST` or `PGUSER` was injected. Formal execution still requires the existing application PostgreSQL connection and existing principal/project/trial/approval selection described in [ProductionConnection](../../../ProductionConnection.md). The local synthetic desktop/CSV path does not require those and has separate prior target-machine evidence; this Python lifecycle change has no new Windows binary/UI qualification. No value from a credential was printed.
