# Base-cohort single-window result: read-only ACK

Conclusion: UNKNOWN / NOT_PROVEN. First target commit returned. The second target commit was genuinely entered and failed in its `_recheck` at the original composite Run predicate. Original scope exit and final deadline success remain unproven. This report requests no further execution, grant or observer.

Execution HEAD: `bdcdce6248fb97b99f0c957aff85682a1cabfbee`.

Run originals: `/tmp/sim2act-authorized-base-cohort-g0-8caa408a1d4847789f04e118972f474f/runs/base-cohort-g0-8caa408a1d4847789f04e118972f474f`; parent summaries `outcome-analysis.json` and `independent-cleanup.json` in its parent root were also read. Raw `diagnostic.json` was read as JSONL, selecting child_final, rather than treated as one JSON document.

Direct observations: parent/child classification UNKNOWN; author outcome records launcher exit 2. Work wall 342.2903028850051 seconds; G0 observation 30.890151267994952 seconds. Six raw Mock exchange lines, eight method entries, two Source delegates, prefix proof zero real models and SYNTHETIC_PREFIX_NOT_REAL_PRODUCTION_QUALIFICATION. Candidate route OWNED / native:issuance. Ordinal 1 has returned=true and copied authority deadlines. Ordinal 2 has returned=false, DomainError and no returned deadlines. Original scope returned=false; both_commits_returned=false; complete=false; final_deadline_check=NOT_PROVEN.

Direct error: VERSION_CONFLICT, `Run identity, cancellation, version or finite lease changed`. Captured stack is advance_model:3752 → diagnostic observed wrapper → original commit:3001 → `_recheck`:2896 → `_require_run_context_row`:869. Thus this window reached the second commit's original body, unlike the preceding window that failed constructing its second-prefix argument.

The exact frozen source evaluates `_cold_commit_prefix(..., "second")` before invoking cold.commit. The genuine second-commit stack therefore proves that prefix construction returned. The original target `_cold_receipts`, subsequent Attempt readback/assertions, parse, usage equality, output validation, receipt_for and settlement-parsed add precede this invocation. Their traversal, including the issued native exact receipt pair, is supported by source ordering and the later stack. There is no separate receipt-phase counter, actual receipt-root name/index m observation, or first-return timestamp. These inferences must not be presented as directly recorded intermediate phase events.

The refusal's exact false conjunct is unknown. The original Run predicate covers expected version/fence types, row existence, principal/project/runtime identity, resources, RUNNING status, cancellation false, version/fence, finite created_at/lease, approval/creation/current-time relation, and current time before the minimum of lease/run duration/contract expiry. The failure-site row and at value are not saved. Earlier RunCheck metadata is checked_at 1792583714.7541528, deadline/lease_until 1792583722.70598, version/fence 1/1; it is an earlier row read, not the second-recheck snapshot. Selected admission diagnostic is NOT_REACHED and no rejection end/stop exists. Neither a unique lease cause, exact excess, first return within its lease, nor `G0 wall - 30` is justified.

Five-stage observed codec metrics (successful returned bytes; observed thread CPU, not whole-process CPU/RSS):

| Stage | Calls | Cumulative returned bytes | Codec thread CPU ns |
| --- | ---: | ---: | ---: |
| _prepare | 3587 | 2410829341 | 9396824421 |
| _graph_run_context | 664 | 486579200 | 1932932582 |
| _graph_pb_accounting | 95 | 69653905 | 278027483 |
| _graph_resolve_trial_source | 993 | 746566755 | 2929294479 |
| _graph_pb_archive_chain | 9 | 6826563 | 27622339 |

Total 5348 calls, 3720455764 returned bytes, 14564701304 thread CPU ns (14.564701304 seconds), independently summed from raw child metrics. Compared with the preceding actual window, _prepare is 3628→3587 (41 fewer); the other four counts remain 664/95/993/9. This is not the local fixture's 15→2 multiplied across all G0 work, and different exit points plus nonzero instrumentation prevent a whole-G0 speedup or deadline-sufficiency conclusion.

Recorded child-before/after and parent-after-cleanup source digests all equal `d74b3b4c73c3f18839b0b5e18b3ead5709d2e713d21d8d7fc11cfddca132a8a8`; profile `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f` is unchanged. Current relevant source/test bytes independently match the archived map and previously reviewed final freeze: cold_accounted `87b0c464866ac038140d615182d1dc552c83dd53cbf629a9bad2b4973bad017e`; runtime `d0140af82c18f1b5181e6ffa929189d7dbd9ac49431a980710792c31d62628c7`; test `5a26147d2bcd8079c1f820ecae579ff8a065e2744e6aa6b32074dcbcae4aba6e`. This review did not rehash the complete dependency environment or revalidate the author's separately reported seventeen prior-original hashes.

Cleanup: child THREADS_CLIENTS_CONNECTIONS_CLOSED, parent OWNED_GROUP_EMPTY, finalization_errors empty; independent-cleanup.json agrees. Reviewer independently observed no parent PID 60685, child PID 60709 or member of child PGID 60709. Logical issuance resident/live 458430612, peak 478097556; after-scope resident/live zero and active=false. These are accounting values, not RSS. Disk monitoring is explicitly sampled budget, not hard quota: 6795 samples, peak allocated 2273280 bytes. Authorizer denials=0. W5 is labeled STATIC_STOP_BEFORE_NEXT_STATEMENT_NOT_AN_OBSERVED_COUNTER. Retained fixture DB was not opened by the reviewer, and is not claimed deleted.

Minimum remaining boundary: the second original composite Run gate and remaining `_recheck`/commit verification must return, followed by normal original context completion and final deadlines. This window established genuine second-commit entry only; it did not establish completed G0, full PB, W5/G1/finalguard, production/account qualification or model readiness.

Reviewer performed only source/evidence/process reads and /tmp report writes: product import/test/DB/Worker/Mock/G0/launcher execution zero, repository writes zero. No retry or new authorization is implied by this ACK of the actual failed result.
