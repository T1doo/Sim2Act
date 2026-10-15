# Independent source-read cases and one observed Cold — 2026-10-15

The fourteen source-read cache counterexamples are now independent of the five-slot trial prerequisite and **all fourteen actually passed**. The one authorized instrumented normal Cold integration **failed after successfully completing its prerequisite and extraction**. Overall status remains **NOT_ACCEPTED**. This slice changes only tests and documentation; production source, cache boundaries, software qualification, guards, deadlines and budgets are unchanged.

## Exact finite change

Base/local/remote P-B candidate was `0c16fa98a94fd1b0a33a080efeb6a0098de4f98a`. Work continues on independent branch `dev/pb-source-read-cases-20261015`; frozen executed source/test commit is `01e93ff7338adf0775d865e5ccde96f17dd51cbd`. Only `tests/test_pb_source_reads.py` and `tests/test_pb_trial_dispatch.py` differ under src/tests/pyproject from that base. The original normal Cold function AST is unchanged.

The new module uses existing `apps.ready(style="ordered")` Generate3, original enqueue and `drive_to_success` with the original Worker/captured MockTransport adapter. Its source made two actual offline model-node sends, finished SUCCEEDED in one real Worker claim, and had two VERIFIED MOCK Attempts. It then calls complete `pb.source` and backs up that actual database for the isolated counterexamples. No success, typed result, receipts, source history or lease is fabricated. Original bounded driver checks current ownership, original created_at/natural_spec_clock and unknown state before any further claim; no extra claim was needed here. Limits derive from actual fixture settings and are copied per case. No trial budget is installed for this generic source fixture; these tests do not replace same-trial account/RPM/Generate3/Source2/Cold2 acceptance or demonstrate quota coordination across databases.

The exact fourteen original parameter branches and all twenty-two Assert AST nodes were preserved: `nested_copy`, `write`, `failed_write`, `limits`, `store`, `authority`, `recursion`, `exit`, `exception`, `user`, `project`, `source`, `thread`, `limits_mutation`. Each starts with the complete real source proof; existing recursive-inflight injection remains a rejection test after that first real proof. The only moved function-body adaptation is per-case Limits construction. No cache was widened and no production defect fix was needed for this group.

Raw `ACTUAL_SOURCE.json` retains an imprecisely named `lease_and_run_timestamps_unchanged: true` fixture field. It means no manual fixture rewrite/extension; it is not a numeric invariant. Original Worker claim/renew/terminal processing naturally changes lease_until/fence/status. Created_at/natural_spec_clock checks are the explicit driver assertions. The raw bytes are preserved with `SOURCE_LEASE_METADATA_CLARIFICATION.md`; the field is not used as an independent timing oracle.

## Actual terminal results

| Batch | Result | RC | Wall time |
|---|---|---|---|
| independent-source-cases | 14 PASS / 0 FAIL / 0 ERROR / 0 SKIP / 0 INTERRUPTED | 0 | 102.459s |
| one-observed-cold | 0 PASS / 1 FAIL / 0 ERROR / 0 SKIP / 0 INTERRUPTED | 1 | 446.365s |

Both batches captured503 src/tests/pyproject files and verified unchanged before/after/copied/root/Git bytes, unchanged frozen HEAD and clean tree. Known restricted SQL/UDF/barrier imports had **zero attempts and zero loaded modules**. Full-source plus both changed-test Ruff PASS; observer F/E9 syntax checks PASS. Mypy was not rerun because production source is unchanged; the prior five baseline errors in status_report.py/tools.py remain unresolved and no green type-check is claimed. PostgreSQL, Windows, native browser and human semantics/owner are NOT RUN.

## Exactly one Cold observation

The runner enforces exactly `tests/test_pb_trial_dispatch.py::test_pb_full_actual_worker_extraction_and_cold`, with one exclusive attempt marker, timeout900, prelaunch observer hash and postrun unchanged-observer check. No pilot, second Cold, fault suite, whole29 retry, alternative SQL/private/UDF diagnostic or model/paid API was run. Observer SHA `e50996adb51c6c9e42dc9f8e7ea877bcb70dfd77ec3011a760ee347bf967a1a2`; runner SHA `de346696199067bffee56f51edff4a65890d35e092284a43c78b37424df8f6d3`.

The observer calls each original public function/context manager once with original arguments and yields the original connection. Only original BEGIN IMMEDIATE events and public transaction/guard/heartbeat/bound/commit_guard/admit/source/extract boundaries are logged. No new SQL, SQL parameters, private bodies, cell hooks, source writes, settings or clocks are introduced. The high-frequency source_scope_gate wrapper was omitted. All3 Engine listeners and9 original callables were restored at pytest_unconfigure.

Actual run: the five-slot source prefix succeeded; controller extraction, exact original-key GET recovery, unchanged-table snapshot assertion and complete raw/canonical source archive checks all passed before queueing Cold and invoking its original Worker. Failure is the normal test-body state assertion at line258: Cold returned **WAITING_RESOURCE**, public error **Heartbeat renewal could not acquire the database lock**. It is **1 FAIL, not a setup ERROR**. Cold Worker entered and executed; it must not be described as entirely NOT RUN. The later seven accepted slots/7000 tokens/14 archives/Cold send-count assertions were not reached, and no new seven-slot-success receipt was produced. The nine extraction fault cases and five Cold fault cases are NOT RUN in this continuation.

Public capture contains1559 records,160 transactions,160 BEGIN spans and303 public-call spans. Drops, pending BEGIN, incomplete transaction/call spans, duplicate boundary keys and observer stack mismatches are all0. Public admission stages recorded generate/source; no Cold admit entry was observed. This is a phase boundary and is not a direct measurement of Cold transport-send count or runtime cache-hit/write-epoch count.

## Distinct public windows in the failed Cold invocation

Cold Run `run_d7c2fcbe93334672832764b12a342e7a`, Worker.process span575, main transaction576:

| Observed window | Elapsed seconds |
|---|---|
| Original BEGIN driver execution, span577 | 0.000097520 |
| Store.tx request to acquired connection | 0.000288319 |
| Acquired transaction body | 29.473680046 |
| Original context-manager exit window | 0.003422550 |
| Public commit_guard span583, inclusive | 9.539413867 |
| Public commit_guard span592, inclusive | 8.342382754 |
| Cold heartbeat BEGIN SQLITE_BUSY, tx589 | 5.042164203 |
| Cold heartbeat BEGIN SQLITE_BUSY, tx596 | 5.268801332 |
| Cold heartbeat BEGIN SQLITE_BUSY, tx603 | 5.201586579 |

All three Cold heartbeat BEGIN-error windows on another thread and the same Store are contained within the acquired main transaction body. Main BEGIN acquisition and subsequent validation/business body are distinct measured windows. This supports local writer contention in this instrumented sample. It does **not** measure pure lock-wait or CPU time, precise lock-release instant, exclusive lock-owner causation, a particular helper as root cause, or general capacity/performance. Nested public durations overlap and must not be summed. No cache gain or successful minimal Cold fix is inferred. Raw public records, paired windows, derived analysis, focused Cold view and independent recalculation are all retained.

## Retained acceptance limits and delivery

The independent generic source counterexamples are now14PASS; same-trial Cold integration remains failed. No production code/cache enlargement, source/authority deletion, lease/deadline/account/approval extension, timestamp rewrite, expired-source revival, guard skip, unknown-result resend or forced pass followed. The integration attempt ended and no further Worker/test invocation was performed after its failure. Real model/paid API calls0; LIVE remains closed. Real fee/account/nonchargeability, full live P-A/P-B, semantics/owner, old-database upgrade, deployment and remote CI are NOT RUN. Original full389 **388PASS/1FAIL/RC1 remains NOT_ACCEPTED**, peer_version unfixed.

The previous [P-B candidate report](PBTrialWorkerWiring20261015.md) and its complete failure archive remain byte-for-byte unchanged at the base, including initial9PASS6FAIL, normal heartbeat-lock failure and both29 setup-ERROR batches. Prior archive SHA `f7ad90d50488e50c8b1f1b74610dcddf0df175d15428120f1394b5300c2adb1d` is preserved. New evidence is in `docs/evidence/pb-source-read-cases-20261015/` with MANIFEST.json, ARCHIVE.json and `source-read-cases-evidence.tar.gz`. Final ordinary branch push/remote/full SHA/15 protected refs/unchanged unrelated WIP/clean0-0 are verified separately after sealing; no remote CI success is implied.
