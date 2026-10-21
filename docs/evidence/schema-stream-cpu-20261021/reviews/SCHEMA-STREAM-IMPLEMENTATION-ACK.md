# Fresh schema streaming implementation ACK

Read-only review. Reviewer ran no product imports, tests, DB, profiler, Mock, G0 or signals and changed no repository files. This is a limited implementation/evidence ACK, not a runtime authorization or final complete-chain result.

Reviewed SHA256:

| File | SHA256 |
|---|---|
| `src/sim2act/_cold_policy_segment.py` | `2fa95de647fb3af98f476a8530aa626c9ac330e45a42ef8b57025a2c0d0fade8` |
| `src/sim2act/_cold_base_segment.py` | `3727954702d37d26ca2d3d26075caaa6c91112f0f51abf0601f2ed64c9b60d81` |
| `tests/test_cold_schema_stream.py` | `d28f25b86bdc8f10e021e666e69ef379213b3cbcd02761a749e63725f96e5d79` |
| `tests/test_cold_policy_segment.py` | `5d6cbf4aa90440fc8d029c75fad3bbb7fc75ce8fdeeba898397409f6a24f2f5c` |
| `tests/test_cold_profiled_candidate_tail.py` | `776097ef17f9c4500562a593ea5a3c87d5168b59475646591f1aa18deef44e4a` |

No remaining concrete P1/P2 blocker was found in this slice. The only product changes are the new strict matcher, its `_fixed_schema` use/identity gate, and its base eligibility identity witness. Default routing, guards, dynamic witnesses, deadlines, SQL, wire bytes, fingerprinting and pickle are unchanged by the inspected diff.

The matcher retains the original schema-object identity short-circuit before recursive matching. Its complete live traversal continues after type, length, order, key or scalar mismatch: each recursive call executes before mismatch combination. Dict exact-string-key validation precedes its child traversal, and active-path checks preserve original cycle errors. Exact native scalar tag plus identity-or-equality preserves same-object NaN and signed-zero semantics; bool/int remain distinct. Unknown objects, bytes and container subclasses remain opaque id leaves without their equality/iteration/reduction callbacks. It retains no completed or cross-call PASS memo, so repeated DAG occurrences are compared against their respective expected branches. Bootstrap shape and retained code leaves remain intact. Replacing the matcher selects ineligibility before executing that replacement, both in `_fixed_schema` and the base witness.

The 23 new test cases include all 59 real bootstrap schemas and each top-level field replacement, type/container/order/opaque identity cases, repeated live mutation, NaN identity, shared DAG against distinct expected branches, and late bad-key/cycle after earlier type/length/order mismatch. Test source compares both boolean results and original DomainError code/message. The strengthened two policy differential cases use strict `exact_output` for the original outputs as well as original fingerprint/at/deadline assertions.

Read author output: `schema-base-regression.log` records **41 passed, 13 deselected in 30.72s**; `policy-strict-regression.log` records **2 passed, 21 deselected in 4.34s**; `mypy.log` reports no issues in two source files. These are author executions, not reviewer executions, and this report does not sum overlapping selections as unique coverage. The earlier `schema-difference.log` records an earlier 16-case stage, not the final whole new file.

`schema-cpu.json` describes six unprofiled, alternating-order rounds over 59 schemas, 25 iterations per round. Recorded medians are old full shape **0.1841236175 CPU seconds**, streaming witness **0.100834649 CPU seconds**. This is a component observation only. It establishes neither complete-chain CPU improvement nor real G0, lease, RSS or performance qualification. The earlier cProfile's 17.224 cumulative schema seconds are not a promised saving.

The profiled test now contains `cap.new_case()`. That is a harness correction after the prior recorded failure and is not evidence of a rerun or a retrospectively passing profile. The planned final unprofiled complete normal chain must be judged on its own frozen source and actual results, including original scope/deadline/receipt assertions. No new G0 window is approved by this ACK.
