# Authorized tail-cost window result review

Decision: **ACK for the evidence and its limited failure classification; G0 remains unsuccessful**. The one recorded execution ended UNKNOWN/exit 2 with original scope completion and final deadline NOT_PROVEN. This review authorizes no retry, new grant, architecture change or relaxed safety gate.

Execution root: `/tmp/sim2act-authorized-tail-cost-g0-2249ab3a0f594bd180944f70bd7ad7ec/`. Execution and independently read current HEAD: `0a6b8f886c485b138a2ef87abbe4bc42f666e35f`. Source-manifest digest recorded in invocation and child before/after plus parent cleanup: `bca95a150c371a4e8f921fa713dbf7cabce506a80e0772d90a3bc01aa27ec0b6`. Profile SHA-256: `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`.

Reviewer scope: read-only original JSON/logs, frozen diagnostic source and source locations, metadata hashes and process-list inspection. The reviewer did not execute product, tests, DB/SQLite, Mock, model, Worker, G0, profile or signal; did not open/hash/decompress the database or change repository/source. Only these `/tmp` reports were written. The full aggregate source digest is cross-checked as reported metadata, not independently recomputed from the full manifest; critical diagnostic file hashes were independently matched.

## Actual result and boundaries

The parent argv observation and invocation both use the absolute frozen launcher script and the explicit candidate flag. The recorded single grant has its consumed marker, and the directory contains one recorded run. The receipt says UNKNOWN with `Boundary: child incomplete or unknown`; launcher log agrees. The diagnostic's original exception chain is VERSION_CONFLICT, `Run identity, cancellation, version or finite lease changed`, at original second `commit` -> `_recheck` -> `_require_run_context_row`. First commit returned; second prefix returned; second commit entered and raised. Candidate route was OWNED, but `both_commits_returned=false`, `original_scope_returned=false`, `complete=false`, final deadlines null and final check NOT_PROVEN.

Actual counts are six recorded request/response exchange records, diagnostic exchanges=6, methods=8, Source delegates=2. G0 wall was 31.21108553600061 s; total supervised work was 342.617473903003 s. These are different intervals. No first-commit return timestamp was recorded. Neither first return nor G0 wall minus 30 establishes a successful or precise final lease return time. W5 is excluded by the original stop-before-next-statement control flow, explicitly not an observed zero counter; no Cold2/W5 success is claimed.

## Tail cost observed in this interrupted execution

| Region | Wall ns | Thread CPU ns | Original check calls | Outcome |
| --- | ---: | ---: | ---: | --- |
| Second prefix | 56237143 | 56233534 | 8 | 1 return |
| Second commit inclusive | 3585821897 | 3585700599 | 436 | 1 raise |
| Nested recheck | 2247529643 | 2247471100 | 273 | 1 raise |
| Inclusive commit minus observed recheck | 1338292254 | 1338229499 | 163 | Derived partial residual |
| Original context exit method | 26090 | 26079 | 0 | 1 method return |

All four span input-key counts are zero. Independent arithmetic matches the reported residual. The residual is measured work before/unwinding the observed rejection, not the cost of the remaining successful second commit or all-child-exclusive work. Codec rows are innermost: second-prefix 10 calls/7746993 returned bytes/30621855 thread CPU ns; second-commit row **excludes** recheck and has 163/126776347/548723665; recheck has 274/213117105/922421088; exit has zero. Across nine observed regions, codec totals are 5795 calls, 4068096209 successful returned bytes, 16242657508 inclusive thread CPU ns. This is neither complete G0 CPU nor directly observed SHA traffic.

`scope_exit returns=1` records only that the original exit method returned. Its actual return value was not separately sampled. False propagation of the body exception follows from the original contextmanager semantics and the observed continuing exception chain; it is a source/control-flow inference, not an independently recorded boolean. This short exit did not execute a successful post-yield scope completion; CandidateObservation independently remains `original_scope_returned=false`/NOT_PROVEN. Tail COMPLETE_OBSERVATION means bounded instrumentation completed, not successful business completion.

Instrumentation uses monotonic wall and foreground thread CPU clocks and has nonzero additional overhead, explicitly not comparable to historical observer configurations as a performance acceptance. None of these costs can be extrapolated to a successful full tail or prove a lease-fixing speedup.

## Post-failure Run evidence

The single failure record matches the original Run message and is marked `POST_EXCEPTION_EXISTING_SAFE_ARGUMENTS_NOT_SHORT_CIRCUIT_TRACE`, incomplete=false. Of 22 recomputed booleans, 20 are true; only `before_lease` and `before_min_deadline` are false. Original supplied `at=1792586396.782219`; read lease/minimum=1792586395.6106474; run deadline=1792586611.745434; contract expiry=1792587856.052482. Independent subtraction gives `at - lease = 1.1715714931488037 s`.

This supports an expired lease comparison in the safely read post-failure argument state using the original supplied clock, and distinguishes it from the still-future run/contract limits. It does not replay original guard callbacks, establish the complete original short-circuit trace, or convert the selected context's conservative UNKNOWN origin classification into a globally unique cause. The older prepare run-context checked_at is not the failure at. No fresh time, SQL or validation replay was used by this diagnostic/review.

## Limits and cleanup

Original recorded limits remain six exchanges/eight methods, prefix 480 s, G0 supervisory 120 s, work 600 s, TERM/KILL 5+5 s, sampled directory 67108864 bytes. Read-only authorizer denials=0; no protection/budget failure is reported. The frozen guard and launcher hashes match their previously reviewed bytes. No real model/account qualification follows from the synthetic test-only SQLite path.

Logical candidate issuance resident/live=458430612, peak=478097556, work=188404034025305936651508; after scope active=false, resident/live=0. These are the admitted logical ledger quantities, not measured process RSS, actual live Python/GC objects or CPU quotas. Disk monitor reports 6798 samples, peak logical=2295786 and allocated=2314240 bytes, maximum completed-sample gap 0.12782756800152129 s. It is sampled directory monitoring, not a hard quota or scheduled exact 0.1 s sampler.

Child final record says THREADS_CLIENTS_CONNECTIONS_CLOSED; parent receipt says OWNED_GROUP_EMPTY, finalization errors empty. The separate cleanup record says parent 64011 and child/PGID 64035 absent and group empty; reviewer process-list reads independently found neither PID nor any PGID 64035 member. No signal was sent. Receipt after-cleanup source digest matches child before/after and invocation. Old-evidence preservation is recorded by author preflight (19+17 originals); reviewer did not reopen the older DBs or claim independent full old-artifact verification here.

Any subsequent proposal involving transaction boundaries, heartbeat or readset/CAS requires its own complete freshness/authorization/fence/TOCTOU proof and review. This evidence does not authorize extending the lease, caching validation or a new window.

## Key raw SHA-256

| File relative to execution root | SHA-256 |
| --- | --- |
| invocation.json | 486ae0d15dc201e3f8f38333f7a9a347967eb6b5565500f9a6e3e9ba1c36234b |
| parent-argv-observed.json | 160abeaa331b23292cb8fce0e754a9630762794ed7e5f2d1d9c1430a30bb5187 |
| grant.json | bc958170f32b658c8f5feb8bbd1a411289aefee63d4c3560d5cd87c58f7e76a4 |
| grant.json.consumed | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| independent-cleanup.json | 2c2ab7a54ec1dc90f92b12e755db14bcea4acc95cd0bbea1e32bc06f2e73b799 |
| runs/tail-cost-g0-2249ab3a0f594bd180944f70bd7ad7ec/receipt.json | a92b31bf63f3d69e6d089ebdf6e95daf093b050fb2ea7151c65fbddda19993b3 |
| runs/tail-cost-g0-2249ab3a0f594bd180944f70bd7ad7ec/diagnostic.json | bc06e22ad5fe3eff9c5e65552d362028018aaaf45ab19b4abfcb08510512317a |
| runs/tail-cost-g0-2249ab3a0f594bd180944f70bd7ad7ec/control.jsonl | 6174643c194bc71ca520a1860bcc4803d8a627a61d86e2381b19b747ef60c96c |
| runs/tail-cost-g0-2249ab3a0f594bd180944f70bd7ad7ec/mock-exchanges.jsonl | fb0142b0ffd9a75ee3669236d39db9908bf5300738171e44ae54d099c6c38921 |
