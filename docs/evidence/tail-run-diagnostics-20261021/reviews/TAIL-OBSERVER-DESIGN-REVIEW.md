# Tail observer design review

Decision: **CONDITIONAL DESIGN ACK ONLY**. The proposed diagnostic-only launcher shim is a reasonable next implementation slice under the conditions below. This is not a code ACK, test result, resource/performance qualification, grant, or authorization to run another window.

Reviewed repository HEAD: `d665c69074e3d97c3332e65a933bb0eaa4dd118d`. Review performed by reading existing source and hashing the six listed files. No product, test, database, model, Mock, Worker, G0, launcher window, signal, or profile was executed. No repository file was written. There is no exact proposed observer source yet to certify.

## Original control-flow facts

- `_require_run_context_row` is one short-circuit predicate. It computes the selected binding before `require`, and invokes `_trial_result(..., _guard)` for finite timestamps. An exception at this wrapper boundary therefore does not by itself prove that the final Run predicate rejected, or that the lease conjunct was the cause.
- The second `_cold_commit_prefix` is evaluated before calling the second `commit`. A prefix exception means that commit was never entered. Its span must remain separate.
- Second `commit` calls `_recheck`, then performs additional original context, finite-bound, authority, pin, stop and final time checks. A successful first commit alone does not prove these later checks or the original scope return.
- `_cold_model_before` performs original final record/deadline checks after its yield; scope closure includes the final graph check, then the final stop/time check. `StopBoundary.wrap` surrounds that original context and deliberately raises `G0Stop` after successful original return. The proposed scope proxy must observe the original context **inside** StopBoundary, not classify this outer stop signal as an original scope failure.

## Required diagnostic boundary

1. Invoke the wrapped original exactly once, with original arguments. Return its exact result on success. On failure, capture metadata within a protected diagnostic block, then use bare `raise` to retain the original exception and traceback. Any diagnostic `BaseException` must only mark evidence INCOMPLETE, never replace the original return/error or prevent cleanup. This applies to clocks, counters, eligibility, metadata and report production.
2. Failure predicate fields must be labelled **post-exception recomputation using the original supplied at**, not the original evaluated short-circuit trace. No `_guard`, `_trial_result`, SQL, fresh `time.time`, model dump, serialization, hash or graph traversal may be invoked to recreate the failed decision. Multiple false comparisons are evidence, not a unique causal diagnosis. Callback/guard-origin exceptions remain origin-undetermined.
3. Extract only a fixed field subset from supported known row/model representations. Validate exact scalar/container types before equality, ordering, finite checks, arithmetic or formatting. Missing/unsupported/oversized values produce null/unknown plus INCOMPLETE; do not invoke foreign `__eq__`, truth, float, repr, mapping or property callbacks to obtain a result. Store only bounded scalar observations, not the row or arbitrary strings/integers. In particular, recording the original `at` does not establish that the remaining argument state was unchanged during the original guard calls.
4. Eligibility must be the already selected exact target instance/guard, original second-prefix boundary and owner thread; no first commit, post path or non-target invocation acquires new business validation. Repeated/unexpected entries invalidate evidence without growing storage or rejecting/retrying product work.

## Span and counter contract

Use fixed buckets for second prefix, second commit inclusive, its observed `_recheck`, and original scope `__exit__`; derive the labelled second-commit remainder from inclusive minus observed nested recheck. The four requested reported regions may present the remainder rather than duplicating the inclusive total, but preserve sufficient inclusive/recheck values to audit subtraction. This is not exclusive CPU for all internal work. Nesting and same-thread clock validity must be verified; negative/missing/unbalanced differences are incomplete, not clamped to zero. A failed recheck yields partial spans, never a completed remainder.

Count real calls to check/input_key/codec without calling them again. Codec byte totals count only actual successfully returned exact bytes. Counter families may overlap and must be labelled accordingly; bytes are returned codec bytes, not a separate SHA input observation or extra serialization. No input walk, per-call trace, hot-path I/O, new pin or hash is allowed. Not-reached is null, distinct from an observed zero. Wall/thread CPU includes observer overhead; this instrumentation is not a performance acceptance result.

The context proxy must call the original `__enter__` and `__exit__` once each when applicable; preserve the exact exception triple and original exit return/suppression behavior. Enter failure must not trigger exit. Body exception, original exit exception, suppression, generator-context exception identity and diagnostic failure during exit all need counterexamples. A small direct delegation proxy is easier to audit than recreating contextlib throw/suppress rules. Observation belongs in protected finally paths and must not change the success semantics already recorded by CandidateObservation.

## Minimal implementation-review evidence

Fake clocks/counters and non-business fakes should cover original call-once and exact return/exception identity; short circuit/guard-origin failures; foreign metadata zero callbacks; original at with mutable arguments clearly labelled; unsupported/bounded metadata; first/non-target bypass; nesting/partial and missing spans; counter overflow/repeat; clock/report failures; exact context enter/exit/suppress/raise behavior; and scope positioning inside StopBoundary. A real future frozen shim diff and author test originals are still required for code/test ACK. No new business window follows from this review.

## Bound source SHA-256

| File | SHA-256 |
| --- | --- |
| scripts/diagnostics/g0_prefix.py | b42a5e104ee595f1633414a84a8e90c44788e1b6f06a45c5eb8f8df28680d5c9 |
| scripts/diagnostics/g0_guard.py | 812a01a06ebb2694d68d50c3a02fd08c8266772cf036a54b0e364e0f9bfe5812 |
| scripts/diagnostics/g0_stage_observer.py | a8395c9494edd2409017deb2da966dc5b61733b0aed07df382e3fab2e3665f6d |
| src/sim2act/natural_spec_runtime.py | d0140af82c18f1b5181e6ffa929189d7dbd9ac49431a980710792c31d62628c7 |
| src/sim2act/natural_live_admission.py | 84195d0061f965b8f1cc2e1bc385941c2739e09dce02293596b3025f14b4433a |
| src/sim2act/pa_spec_apps.py | 6197df6c98bf1eeff463c7fc7b99c9c48e9fe308969fde8243715091a31712d6 |
