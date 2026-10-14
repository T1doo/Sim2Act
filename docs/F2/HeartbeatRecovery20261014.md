# Guarded SQLite heartbeat recovery

Previous delivered source: `33189240e8be34dccf76ce4c08ad9eebfc0bd58b`. Implementation core: `0cafd80c752abe61df0fc6e1079eac42e721a780`; qualified source: `7e6b793c922a1751cdd8906ff1dd7eed675113bd`. The 77-file qualification pin is `a442f7ed69b6af89577c55b8d29363fb0e03e859cf05b451c7bd471872aad0d6`, using the existing config exclusion and pin-only normalization. Original baseline, anchors and compatibility rules remain unchanged.

Ordinary synthetic business logs on the unchanged previous source confirm underlying SQLite driver code 5 / SQLITE_BUSY: background heartbeat waited about five seconds and exited while foreground work continued. The baseline PB correction passed, but that is not evidence that its heartbeat was healthy. Its old heartbeat returned no committed lease value; recorded success call-time bounds are explicitly approximate, and missing old precise timing is not reconstructed.

The background loop now retries only SQLAlchemy OperationalError with a genuine sqlite3 driver BUSY/LOCKED code on SQLite. Each batch has at most three attempts with short interruptible delays, bounded by the known live lease and verified original absolute run deadline. Transaction wait is capped downward and restored. Every heartbeat still checks current permission/scope, owner, fence, live lease, status and exact lease CAS. Deadline failure after a write rolls the transaction back. Only a committed heartbeat returns its renewed interval.

After an exhausted contention batch, the loop defers to its original cadence only when an actual guarded committed synchronous renewal advanced the owned interval beyond this invocation’s initial claimed interval and the verified original cutoff remains live. Deferral is not recorded as a heartbeat success, creates no lease and extends no deadline. Unknown, unverified, expired, foreign-driver and non-contention failures retain the original exception and are handed to the foreground before another step. An already completed terminal transaction retains priority over a late background error. Unrelated generic Worker heartbeat loops are unchanged.

Five actual failed PB executions are retained. The first two v8 failures showed that treating exhausted background contention as fatal despite healthy synchronous progress was too strict. The v9 failure then demonstrated three model-node synchronous renewals whose committed lease values were not published to the process scheduling state. All three original renew sites now publish the committed numeric interval under the invocation-local lock. The v10 fresh PA/PB cases passed, but two actual PB corrections then failed because no renewal happened inside the last retry batch despite a previously advanced still-live lease. At the first failure the lease still had 6.30 seconds; a synchronous guarded renewal committed 0.83 seconds later. The final invocation-scoped comparison accepts actual committed progress since claim, instead of requiring progress inside that batch. Completely absent progress and expired intervals still fail. This state is scheduling metadata, never an authorization proof. Existing model deadline, reservation, sender, callback, settlement and final commit gates are unchanged; no model/tool/token/run/lease budget increased.

Actual-source independent review found no new static blocker and confirmed all three publication sites and qualification identities. All current-source commands terminated before this evidence was sealed. Previous delivered 65 executions / 62 unique identities and old candidate results are not accumulated into current-source acceptance.

Current modified-file Ruff passes. Mypy reports five existing errors in status_report.py and tools.py. Private UDF diagnostic remains BLOCKED with no retry, rephrasing, reconstruction or replacement. PostgreSQL, Windows, native browser, real/paid models, real human semantic acceptance, full P-A/P-B product acceptance, remote CI and deployment are NOT RUN.

The six actual late synthetic callbacks each fire once: two permission revocations end WAITING_RESOURCE, source/competing versions and owner withdrawal end FAILED (three), and cancellation ends CANCELLED. All six retain no child typed result or save effect. These are successful rejection tests, not successful business executions. Controlled expiry unit tests advance a synthetic clock; they do not claim naturally elapsed lease expiry.

Current frozen-source acceptance is **129 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, **128 unique test identities**. The one extra execution is a PB correction repeat, not new coverage. Qualification/ownership/foundation contribute 73, legacy workflows 43, fresh PA/PB parents two, exact corrections three, late callbacks six and HTTP/offline pages two. Each of the ten suites has the same 466-file before/after closure and the same frozen HEAD; no source changed during a Worker run.

| Actual suite | PASS executions | Whole pytest wall seconds |
| --- | ---: | ---: |
| v11-boundary-qualification | 73 | 20.608 |
| v11-legacy | 43 | 116.116 |
| fresh-v11-pb | 1 | 434.957 |
| fresh-v11-pa | 1 | 226.650 |
| v11-correction-pb | 1 | 276.753 |
| v11-correction-pb-r2 | 1 | 277.386 |
| v11-correction-pa | 1 | 124.351 |
| v11-late | 6 | 180.656 |
| v11-ui-pa | 1 | 135.293 |
| v11-ui-pb | 1 | 302.231 |

Three ordinary original-key public terminal receipts expose exact fence 1, a single claim and SUCCEEDED/result version 2/PENDING/UNKNOWN. Measured accepted-to-terminal-transaction-return times are PB 229.889 and 230.248 seconds (remaining original deadline 70.111 and 69.752), PA 103.065 seconds (remaining 196.935). The observer runs after advance_model(False) has exited its transaction; this is postcommit return timing, not a reconstructed SPEC_COMMITTED event timestamp. Whole pytest durations include preparation, controls and independent review and are not Run lifetime measurements.

The PB/PB-repeat/PA logs retain 7/7/3 contention deferrals, zero background heartbeat successes, zero background halts before terminal and zero foreground fatal observations. Actual guarded synchronous renewals keep these runs live; failed background attempts are not relabeled as successful renewals. Fresh PB logs additionally retain late VERSION_CONFLICT halts after terminal transaction returns. These finite tests demonstrate recovery of the observed contention failures, not universal timing or load reliability.

The PA/PB current in-process HTTP and offline JSDOM flows passed 32 + 34 checks. These are separate assertions, not additional pytest identities. PB's unknown acceptance response recovers by original key GET with one correction POST. No native browser was used. Prior delivered evidence and the five actual failed candidate PB attempts remain preserved without accumulating their test counts into this acceptance. The wrong test filename selection returned code 4 with zero selected tests and is retained separately; its corrected boundary command passed 27.

The ordinary logger retains its legacy top-level call-time-bounds label. For the new source, exact_committed_lease_until is the actual postcommit Store return; separate lease_lower_bound/lease_upper_bound fields are only call-time helper bounds. The legacy blanket label is overbroad and is not used to infer exact lease values. Raw executed logs remain unchanged.

## Sealed evidence

[Complete heartbeat evidence archive](../evidence/logic-correction-heartbeat-20261014/logic-correction-heartbeat-evidence-20261014.tar.gz), SHA256 `1d904a2332df45042ca50d4ede61c10b98d82e6d828a0446f8d90fc2bc8ea5e3`: 7,836 members read back and hash-verified, 47,128,909 compressed bytes. [Archive receipt](../evidence/logic-correction-heartbeat-20261014/archive.json). Prior [effective-scope evidence](EffectiveScope20261014.md) and all old archives remain unchanged.

Actual-source independent FINAL SHA256 `b5790575843bb4f0ae556fc5e8d830ff972b84536a1571f5f9b489aab4cc79e1`, MANIFEST `3216739dc7f480040ba49ba114b6ec4d5a7a4fefb1fcfe2e8893136b748b7749`. Final public-evidence independent FINAL SHA256 `39d5f72e9baf35964c60bfc7c79e0e0dc9f573dfed1cf7006899f4ddbe106cd0`, MANIFEST `85bc7ad596a957ed0208ccc2042acbd1ae259cb0e62adb5691dafa8424632e84`. Reviewer performed zero tests/Workers and adds no dynamic coverage. Its synthetic UI output projection error and an initial asset-path verifier assumption are explicitly retained in its report; neither is a product pass or an erased failure. Normal development-branch push is not CI green, deployment or full product acceptance.
