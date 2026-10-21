# Stage-current composite parent: limited static review

Result: LIMITED_ONE_CALLSITE_DESIGN_AND_PRODUCT_DIFF_ACK; author test results remain separate. This is neither an execution instruction nor a new window/grant.

Reviewer only read source and Git diff. No product import, test, DB open, Worker, Mock, G0, launcher or producer was executed; no repository file was written.

Baseline HEAD: `e4dddb1c8fd9a67a622e5d69c8637e07a38f8836`.

Read product SHA256: `src/sim2act/natural_live_admission.py` = `84195d0061f965b8f1cc2e1bc385941c2739e09dce02293596b3025f14b4433a`.

The product diff replaces precisely the two statements inside `_graph_stage_current._parent_pin` (original `_graph_trial_pin` followed by `_graph_trial_stage_raw`) with the existing `_graph_trial_stage_parent_pin`. No other product statement differs from the baseline. The helper already serves `_graph_run_context` and `_graph_resolve_trial_source`; this adds the third exact callsite.

The existing helper selects the composite only for exact `_OwnedPrewriteMode`, exact `_NativeCandidate` and `owned_ready is True`. Otherwise its original pin-then-stage-raw pair remains intact. The composite first performs the original full graph/store/connection pin, then native ownership/current linkage and the original Generate/Source/Cold relationship predicates. On failure it closes the mode. This change adds no token, cache, reusable permit, reentrant bypass or generalized root rule.

The containing `_graph_stage_current` retains its typed model cohort and `_trial_typed_guard` (parent first, typed values second), original Source/Cold business predicates, query/external-return guards, independent public family/run/stage entry guards, authorization fingerprint, deadlines, final guard, and invalidation on BaseException. Default/native-disabled behavior therefore retains the old helper sequence. No new entry/configuration or account qualification is introduced.

Minimum meaningful local coverage is the actual Source and Cold `_graph_stage_current` path, comparing the original helper adapter and the new helper with the same complete root set. Priming the real lazy Release pointer before the measured comparison is appropriate: first-use graph.add encoding is separate from this callsite. Compare complete family/run predicate sequences, parent invocation count, authority fingerprint and job identity; the expected codec difference is exactly six times the observed parent invocation count. This is a local redundant encoding count claim, not a G0 latency, lease, throughput or production qualification claim. Existing independent entry, typed-cohort and query-return revocation tests must remain.

The currently read test draft (`tests/test_cold_accounted_stage_pin.py`, SHA256 `3d54b1615392eaeea7649cbf7a58e6914630762203bdfaee8b86f1c54b3977f6`) includes those Source/Cold comparisons, exact third-callsite AST check, and cross-call mutation/revocation cases. One test-only refinement was sent to the author: put `pytest.raises(DomainError)` around only the second stage-current call, so an unexpected first-call refusal cannot satisfy a cross-call rejection test. Preserve the original outer scope cleanup and assert closure after the rejected second call. This draft test SHA is intermediate, not a final tested hash.

No product P1/P2 identified in this exact one-callsite diff. Runtime evidence and the final amended test hash have not yet been reviewed here. The preceding actual window's first-commit rejection by 0.5311813354492188 seconds remains a historical result; it does not prove that any local encoding reduction suffices for receipt processing, the second commit and full original scope exit.
