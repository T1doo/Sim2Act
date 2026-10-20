# Frozen stage-observer independent review

Decision: **ACCEPT_FROZEN_DIAGNOSTIC_STAGE_OBSERVER_ONLY_NO_THIRD_WINDOW_OR_PRODUCT_OPTIMIZATION**. No material blocking finding in the exact reviewed patch.

Baseline HEAD: `30977f013dbcf7c9f20d88ccff7ae9d8a25106c0`. Reviewed exact hashes are in REVIEW.json and remained unchanged after testing. The implementation satisfies the scoped preimplementation design conditions; this review does not authorize business execution.

The original _ColdCommitDiagnostics.stage context enters before observer gating and exits after the observer region unwinds, preserving original entry, exception/suppression and exit semantics. The active region covers only the original yield body. The prefix gate requires boundary.entered and exact captured instance identity; the collector additionally restricts observation to its creator/Worker.once foreground thread. Calls outside a region or on another thread delegate without clock reads or metric updates.

Four wrappers time only the original codec, typed storage, raw copy and typed comparison calls. Normal observed calls read thread_time_ns twice. There are 20 fixed aggregate buckets and a 32-frame default stack, not per-call records. Direct child inclusive intervals are charged once to their immediate parent's child total. The resulting exclusive metric is inclusive minus observed child spans only; it includes unobserved child work and residual nested instrumentation and is not pure function body or system-exclusive CPU. The wrapper's own start-up bookkeeping is outside its measured interval, so these metrics do not capture all observer cost.

No typed model attributes are sampled. Input metadata uses only type checks and O(1) len of exact dict/list/tuple/bytes roots; unknown roots remain explicitly unknown. Element counts are not bytes. Only a successful exact-bytes codec result contributes codec_output_bytes; the implementation accurately says it does not observe SHA calls. No extra input walk, dump, encoder, hash, pin, hot-path I/O, payload retention or cProfile is added.

Clock/type/nesting/aggregation errors and stack overflow mark the observer INCOMPLETE and stop further collection. They do not retry or skip original calls, alter their returned objects, or replace original BaseException objects; original traceback frames remain present with added wrapper frames. Active stage and depth unwind cleanly. Incomplete data is explicitly not valid timing evidence. Unreached stages report metrics=null. Prefix report collection happens only after original stage/G0 unwinding in the existing G0Stop or failure handlers, before existing diagnostic archival.

I independently executed only:

`PYTHONPATH=scripts/diagnostics .venv/bin/python -B -m unittest test_g0_stage_observer -v`

CPython 3.12.14: **9 passed, 0 skipped, exit 0**, 0.476 seconds. Raw output: UNITS-INDEPENDENT.log. Tests cover nested inclusive/direct-child-exclusive accounting, five buckets, no foreign attribute/len callbacks, exact instance and thread gating, original context entry/exit/suppression, BaseException identity/frames, injected clock/aggregate faults, finite-stack overflow and cleanup. The 10-second isolated child compares actual pure helper outputs and original diagnostic stage behavior without DB, fixture, model or transport invocation; no graph pin is added. Parent logs separately report 52 total tests / 48 passed / 4 skipped and Ruff success; I did not repeat the broader suite.

I read OVERHEAD-CONTROL.json without rerunning it. Its 10,000-empty-call local difference is about 840.2753 CPU ns/call and is correctly scoped as a single local control, not a bound or G0 forecast. Nonzero observation overhead remains material. Existing historical total-G0/codec measurements stay tied to their original runs and observer; they cannot be combined with this control to forecast lease acceptance.

git diff --exit-code returned 0 for src and all tracked historical evidence. g0_guard.py and g0_bounded.py are unchanged; StopBoundary, sampling policy, disk/byte/time/Mock budgets, lease and authorization behavior are unchanged. No production optimization is included. This reviewer edited only /tmp review artifacts, did not open a DB, run a fixture/Mock/G0/launcher/profile, or repeat the overhead control. A third business window still requires its own explicit authorization and a fresh reviewed execution/grant boundary.

