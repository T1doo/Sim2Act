# Tail diagnostic single window: limited read-only result ACK

Conclusion: ACK_ACTUAL_UNKNOWN_NOT_PROVEN. The second original commit entered and failed in the original Run predicate. The new diagnostic supplies post-exception argument comparisons and bounded partial tail costs; it does not establish completed G0, a successful original scope exit, a production qualification, or a new execution decision.

Execution HEAD `0a6b8f886c485b138a2ef87abbe4bc42f666e35f`; root `/tmp/sim2act-authorized-tail-cost-g0-2249ab3a0f594bd180944f70bd7ad7ec`, run subdirectory `runs/tail-cost-g0-2249ab3a0f594bd180944f70bd7ad7ec`.

Reviewer read raw receipt, diagnostic JSONL, manifest, cleanup/process evidence and frozen source only. No product imports/tests/DB/Worker/Mock/G0/launcher execution and no repository writes. The retained fixture DB was not opened.

Direct result: parent/child UNKNOWN; author reports exit 2. Six Mock exchanges, eight method entries and two Source delegates; OWNED / native:issuance. Work wall 342.617473903003 seconds; G0 observation 31.21108553600061 seconds. First commit returned with eleven copied deadlines and no return timestamp. Second commit entered and raised VERSION_CONFLICT `Run identity, cancellation, version or finite lease changed`; trace reaches original commit:3001 → `_recheck`:2896 → `_require_run_context_row`:869. Original scope returned=false, both_commits_returned=false, complete=false, final deadlines absent, final check NOT_PROVEN. Original admission rejection end/stop diagnostic remains NOT_REACHED.

Tail report is COMPLETE_OBSERVATION, which means the encountered instrumented spans were observed consistently, not that the business interval completed. Original second prefix returned; receipt/Attempt/parse/usage/schema/receipt_for/settlement-parsed traversal before the genuine second-commit entry is inferred from frozen source order, not independent receipt phase/root/index m events.

Post-exception Run evidence has predicate_message_matches=true, incomplete=false, and explicitly uses POST_EXCEPTION_EXISTING_SAFE_ARGUMENTS_NOT_SHORT_CIRCUIT_TRACE. Of twenty-two comparison booleans, twenty are true; only before_lease and before_min_deadline are false. Recorded scalars:

- original at: 1792586396.782219
- lease_until and min_deadline: 1792586395.6106474
- created_at + original contract run_seconds: 1792586611.745434
- contract_expires_at: 1792587856.052482

Arithmetic from those original argument values gives at − lease_until = 1.1715714931488037 seconds. This establishes the failed lease/min relation **in the post-error safe argument re-evaluation**. It is not G0 wall minus thirty, not a direct trace of each original short-circuit conjunct, not a first-return timestamp, and not a bound on the improvement required to complete the unreached later checks. The wrapper called the original once with the original at/guard, then read safe existing storage without SQL/time.time/guard replay; the product Run predicate was not changed.

Observed tail regions:

| Region | Wall seconds | CPU ns | CGR checks | Outcome |
| --- | ---: | ---: | ---: | --- |
| second_prefix | 0.056237143 | 56233534 | 8 | returned |
| second_commit, inclusive | 3.585821897 | 3585700599 | 436 | raised |
| observed recheck, included above | 2.247529643 | 2247471100 | 273 | raised |
| commit minus observed recheck | 1.338292254 | 1338229499 | 163 | measured residual only |
| original context exit call | 0.000026090 | 26079 | 0 | returned from __exit__ call |

Input_key counts in these regions are zero. Innermost-region codec rows separately record prefix=10, commit outside recheck=163, recheck=274 and exit=0; native zero input_key is therefore not zero encoding. The residual is parent inclusive minus the one observed child only, with wrapper/bookkeeping/unwinding overhead. It is not all-child exclusive time or the cost of the remaining unexecuted successful recheck/commit path. In particular the inclusive commit and recheck rows must not be summed as disjoint costs. The five older stage codec counts remain 3587/664/95/993/9; no normalized speedup or unchanged-instrumentation comparison is claimed.

Scope exit nuance: raw exit evidence is calls=1/returns=1/raises=0, wall=26090 ns and zero checks. The observer does not record the original __exit__ return value. Its falsey/no-suppression behavior and propagation of the body exception follow from the original generator-contextmanager control flow and later error chain; they are not separately sampled boolean results. Because the body raised, original normal post-yield second-authority/final-hash/final-clock completion did not occur. Candidate original_scope_returned=false and NOT_PROVEN remain authoritative. Tiny exit cleanup time is not the cost of a successful final original guard.

Source: child-before/after and parent-after-cleanup digests agree at `bca95a150c371a4e8f921fa713dbf7cabce506a80e0772d90a3bc01aa27ec0b6`; profile `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f` is unchanged. Independently hashed relevant current sources match the archived map and final reviewed freeze: tail b23c45591ca71b98d04a3c38fa5ccaf0141adf66476edae31ee33b37e8efc4a8, stage observer adacdff642f9dc30693df817c49c28e87114a14e813d7143e323ed14eab00d03, prefix dfe1299c28746db393afa3c26340c87792e7b39d665548f093c1b472151647d4, runtime d0140af82c18f1b5181e6ffa929189d7dbd9ac49431a980710792c31d62628c7. This review did not rehash every environment dependency or older original.

Cleanup: child THREADS_CLIENTS_CONNECTIONS_CLOSED, parent OWNED_GROUP_EMPTY, no finalization errors. Independent-cleanup.json agrees; reviewer independently found no parent PID 64011, child PID 64035 or member of PGID 64035. Logical resident/live return to zero with active=false (peak478097556), not RSS. Authorizer denials=0. W5 remains STATIC_STOP_BEFORE_NEXT_STATEMENT_NOT_AN_OBSERVED_COUNTER. No automatic retry is inferred or requested.

Minimum remaining boundary: original second Run gate and all subsequent recheck/commit deadlines, original second authority, normal scope final complete hash and original final clock must pass. This result locates a post-error lease relation and measured partial tail work; it does not justify extending lease, replaying guards, enabling heartbeat renewal inside the proof transaction, or another window. Any transaction-boundary proposal is a separate source/design review, not an implementation recommendation made by this ACK.
