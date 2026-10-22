# Source independent-process completion — 2026-10-22

**One PASS**, frozen product `ce7f56769e50ba73250f186d51ab8910877e85a9`.
This closes the Source process gap from V5 §8.2–8.3 / F2-T09. No product source,
original guards, clocks, budgets, permissions or dependencies changed. No repeat
of the39/37/20 suites, no CI, G0, Cold2, W5, real model or external business HTTP.

The original owned process20643 executed the real Store.claim / Worker
process_job / ProtocolAttemptRunner / BudgetedProvider / Mock / dispatch path.
Its two known responses and one VERIFIED resource.read produced the real Source
READY Run/last-Attempt mirrors. At the original completion function, a test-only
BaseException boundary asserted that the READY facts were committed and no
PROTOCOL_COMPLETED existed, then interrupted the transaction before its writes.
No response or fabricated seal was imported.

Original process20643 served one local API GET of the still-RUNNING/incomplete
Run, stopped its API, joined all threads, closed its fixture/Store and returned
exit0. Parent wait() confirmed that exit before spawning new API process20647:
reaped monotonic23256.967646271 < new spawned23256.972961899. The old Worker and
old API were in the **same original PID**; this is an independent API process
continuation, not an OS restart or pre-existing separate Worker/API topology.

New API20647 opened the **same original SQLite file**, existing sidecar and
original completion command. It did not initialize/migrate/reset or construct a
runner/Worker. Model request/request_serialized, provider
call/preflight/accept_candidate, Worker reserve/construction, Store.claim and
runner construction had immediate failure witnesses; none was invoked. Three
real loopback requests: completion POST, original Run GET, same-body/key cached
POST. Together with the old API GET, actual local HTTP is **4**, not0. Mock is
**2/2** entirely in the old process; recovery sends/reservations/acceptances are0.

The result's strict canonical JSON equals the exact value computed at the old
completion boundary. Result and business fingerprint, READY, ordered response
associations and full tool receipts remain bound. Source completes only to
**WAITING_APPROVAL / semantic UNKNOWN**, without review, advance or publication.
Same command replay returns the exact response with cached=true.

Actual before/after closed SQLite files compare55 tables: only runs,
protocol_jobs and events changed, all other52 match full row values. Attempt,
slot, Operation, quota/reservation and other accounting were not rewritten;
sidecar bytes/SHA are identical. New API recorded909 cursor statements, exactly
3 UPDATE (the original Run/protocol result) and4 INSERT events, no DDL/DELETE or
new Attempt/slot. `api-sql.json.gz` preserves statements and parameters. The
old process recorded3380 statements **after fixture initialization**, so its log
is not claimed to include the initial schema creation. DBAPI commit callbacks
were not separately counted, and SQL is not claimed byte-equal to normal Source
completion's sequence.

Original Run created_at1800000000, lease_until1800000030; explicit new-process
synthetic clock1800000045; all original provider/Run completion bounds1800000300.
Ready_at1800000014 is unchanged, completion at1800000045 is inside the original
bounds. Lease30/Run300 remain configured; recovery ends lease0 and advances
version1/fence1→version2/fence2, not the original deadline. After completion the
real Store.guard with the old fence rejects before its attempted UPDATE; full
DB snapshots remain identical. This proves the original combined guard rejects
the old writer; it does not identify fence as the sole failed predicate.

## Execution and cleanup

The probe is frozen SHA256
`5f6dc55838dd30026d25b2a99b75d9815433de4a75e73cf012c47146b47b98df`.
The180-file manifest SHA is
`bda6907f7c6088d653275baa19d95f1794c0e8dc0ccf80e9493348c344533daf`,
covering all tracked product sources, the sole used test helper, original lock
files, evaluation contracts and fixture materials. Probe and manifest identities
are checked by parent and children before launches, and source hashes again at
completion. Original Source's nine-file manifest also matched9/9. No code was
changed during execution.

Actual command, exactly once without automatic retry:

```text
timeout --signal=TERM --kill-after=10s 180s /workspace/Sim2Act/.venv/bin/python /workspace/Sim2Act/docs/evidence/protocol-source-process-recovery-20261022/probe.py run /workspace/sim2act-source-process-20261022
```

Work elapsed **2.936233348 seconds**, bounded by180, followed by one shared10s
cleanup allowance. This measures this small instrumented semantic probe, **not
G0 performance or a30s qualification**. Child server stop waits occur within the
work budget; the outer timeout remains the hard elapsed fallback. No forced
stop was needed: both children exit0, all non-main threads empty, Store disposed,
cleanup CONFIRMED/errors[]/denied[]/unknown processes touched0. Post-exit /proc
entries for both original owned PIDs are absent. Temporary original fixtures
remain intentionally archived; they were not falsely reported deleted.

No failure occurred in this one-shot run. Earlier Source development failure
budgets under the sibling protocol-source-completion directory remain untouched;
no failure budget was reset or reclassified. Ruff and py_compile passed before
freeze. Startup/request budget recording was independently reviewed before this
single execution; final review is recorded in `review.md`.

## Remaining acceptance and native UI handoff

This is synthetic SQLite and an explicit business clock, not PostgreSQL
concurrency, a real-provider account, human semantic acceptance, browser pixels
or G0. It does not inherit the historical extract Edge PASS.

A Source-native UI window can reuse **this** `before.sqlite.gz`,
`original-received-sidecar.json` and exact original command with zero new
Source/extract/Worker/model exchanges. Existing browser helpers remain pinned to
extract (`protocol_completion_browser_ci.py` EVIDENCE/completion_path/compiled
assertions, and `browser-ci/extract-completion.cjs` POST allowlist/compiled_plan
checks). A Source-specific, explicit branch must instead assert the exact Source
result fingerprint and WAITING_APPROVAL/UNKNOWN, then retain original-key lost
response, duplicate click, close/return and late-callback checks, plus protected
Edge and cleanup. It must preserve existing180+10s,30business GET/3POST/40static
GET/4screens limits. No new browser window or SDK install is part of this result.
