# Schema stream: profile attribution and design review

Scope: read-only inspection of the author's raw profile JSON, failure log and source. Reviewer executed no tests, profiler, product imports, SQLite, Mock, Worker or G0. This is a design review, not a launch authorization or final implementation/test ACK.

The profiled pytest ended **1 failed in 187.29s**. Its failure was the harness's `(case_exchanges, case_methods) == (1, 1)` assertion, observing `(0, 0)`. The earlier assertion requiring `TailStop.original is None` and `normal_scope_returned` passed. Source places that state after original context normal exit and the deliberate closed-guard rejection. Thus the profile covers the normal original context and closed probe, but the complete pytest/postprocessing did not pass. A missing `cap.new_case()` explains the recorded counter discrepancy; the subsequently edited test is not the frozen profiled source. No profile retry is claimed.

Profile SHA256: `e037518ad04e7f950b6d0a632510e0c8799fc65191c4dc67f14bd6ab8a2955a4`.
Raw cProfile SHA256: `ebac16021c448b87812490501dcf69fca954729bcd2e4f96765436d162ea1ca8`.
Frozen profile manifest SHA256: `aba2e11aa81d97f24ec58872a8b4fd2bdbb1a0b1c726efc804a92ffb3a4e33d3`; its HEAD is `16c3ba0f3c2a2b764f6cc698f34dd9db08da937b`.

The original-C-callback/thread-filter setup is covered by the earlier `IDENTITY-PRESERVING-THREAD-CPU-PROFILE-CODE-ACK.md`. The profile includes profiling cost and main-thread harness SQL parameter copying. It is attribution evidence, not a real-clock performance or lease result.

Direct JSON inspection confirms:

| Frame | Calls | Self CPU seconds | Cumulative CPU seconds |
|---|---:|---:|---:|
| `_pickle.Pickler.dump` | 8,062 | 19.415121942 | 28.090953240 |
| `_cold_graph_bytes` | 8,062 | 2.177022901 | 30.279416114 |
| `_schema_shape` | 1,833,414 | 6.947715798 | 17.223956514 |
| `_fixed_schema` | 10,001 | 0.242469025 | 17.805788754 |
| `validate_model` | 18,201 | 4.117150154 | 19.033155621 |
| `fixed_serializers` | 275 | 0.021887303 | 23.478370519 |
| `_typed_values_from_models` | 275 | 0.002649895 | 16.126927591 |
| `_typed_parameters` | 293 | 0.002018838 | 6.636335473 |
| `_base` | 569 | 0.011566523 | 65.473211255 |

All 10,001 top-level `_schema_shape` calls came from `_fixed_schema`. Of the latter calls, 9,841 came from the base `fixed_serializers` generator; 148 and 12 came from the policy snapshot generators. Total recorded exclusive CPU is approximately 146.82376739 seconds. Recursive cumulative times and caller/callee cumulative times overlap; they must not be added. The schema frame is a concrete Python construction hotspot. Removing that construction does not establish that all 17.224 cumulative seconds can be saved. Complete fresh pickle bytes and the typed validation gates remain required.

The proposed strict streaming comparison is conditionally acceptable if it preserves these exact original `_schema_shape` semantics:

1. Fully traverse every live child even after mismatch. A first mismatch followed by a non-string dict key or a cycle must retain the later original `DomainError`; do not return False early. Dict checks validate all keys before visiting values.
2. Match exact scalar type tags, then identity-or-equality. Same-object NaN matches through the original tuple identity shortcut; a distinct NaN does not. Signed zero remains equal; bool and int tags remain distinct.
3. Exact dict/list/tuple only; dictionary order remains significant. Bytes, subclasses, callbacks and other leaves retain only their original `code-object`/identity behavior. Do not invoke their equality, hashing, repr or reduce.
4. Use invocation-local active-path cycle tracking, with no cross-call PASS cache. Shared DAG occurrences must each receive comparison against their own expected subtree. A completed-by-live-id memo alone would be unsound.
5. Keep `_fixed_schema`'s original live-schema identity short-circuit before recursive traversal and preserve the validator/serializer/method checks. Retain bootstrap `_schema_shape` and its kept code leaves, preventing id reuse.
6. Include the new matcher in the existing fixed base code identity witness; replacement selects legacy rather than assuming qualification.

Necessary differential cases include every bootstrap schema, every scalar/opaque/container branch, changed order and length, same/different NaN identity, shared live DAG against unequal expected branches, and early mismatch followed by late bad key/cycle. No lease, dynamic guard, SQL, fingerprint or pickle change is needed for this candidate.

The draft matcher read during this review implements deferred mismatch/full traversal, exact native branches, scalar identity-or-equality, opaque id comparison and the identity short-circuit. No concrete new blocker was found in that draft. Final frozen source and actual differential/normal-chain results remain separate review steps. This ACK does not permit a new runtime window.
