# Preimplementation stage-observer design review

Decision: **CONDITIONAL_DESIGN_ACK_DIAGNOSTIC_ONLY_NO_THIRD_WINDOW**. This approves only the narrow diagnostic design subject to the requirements below and a later frozen-code review. No third Mock/G0 window is authorized.

Baseline: `30977f013dbcf7c9f20d88ccff7ae9d8a25106c0`. I read the current original _ColdCommitDiagnostics.stage/snapshot and StopBoundary instance/entered capture and unwind paths. No test, product, database, Mock, G0 or launcher was executed.

1. No src modification or business/DB/Mock/G0/launcher execution; this is a diagnostic design only.

2. Preserve original stage context enter/body/exit and call each original function exactly once.

3. Observe only the five original stage bodies of the captured diagnostic instance while boundary.entered; require the owner thread and clear the stage in finally.

4. Use two thread_time_ns readings per observed call; aggregate fixed 5x4 metrics and a stack with explicit finite maximum depth.

5. Compute exclusive only by subtracting direct observed-child inclusive CPU once; no system-exclusive claim or addition of overlapping inclusive values.

6. No typed-model __dict__ or other new attribute reads. Input volume UNKNOWN by default; optionally exact native O(1) container lengths under clearly distinct element/byte names.

7. Codec successful exact-bytes output length may be recorded as codec_output_bytes; do not claim SHA was measured or non-codec field counts are bytes.

8. No extra pins, scans, encodes, hashes, dumps, repr, payload logging, argument retention, cProfile or hot-path I/O.

9. Observer-only failures including clock/stack/aggregation errors mark incomplete and disable observation without replacing the original return or any BaseException; never retry originals.

10. Serialize the bounded aggregate after the original stop/unwind, never inside active business stages.

11. Pure synthetic tests must prove gate/thread/interval exclusions, direct-child nesting accounting, exact original call counts, failure/exception identity, stack cleanup and overflow/failing-clock fallback.

12. Nonzero observer overhead must be explicit; no historical cross-observer performance comparison, G0 speedup claim, lease change or execution grant.

The safest first version reads no typed-model attributes. Even object.__getattribute__(model, "__dict__") may consult a changed descriptor and adds a new possible error/side-effect site; field count has little relevance to byte volume. Exact native container len is an optional shallow element count, never a substitute for complete input size. Successful codec bytes length is already available from the original return; label it codec_output_bytes. It equals the subsequent SHA input on the original input_key path, but this observer does not instrument SHA itself.

Original stage enter/exit and snapshot order must be retained. Set the additional active-stage scope only inside the original stage body. Same-instance, entered and owner-thread checks prevent earlier prefix and background heartbeat work from contaminating aggregates. Failed/ineligible gates should directly delegate without clocks or metric writes.

A bounded frame contains only metric ID, start CPU and accumulated direct-child CPU. Mark overflow, invalid clocks and bookkeeping failures incomplete; preserve coherent cleanup or disable collection. The measured child interval excludes some child wrapper bookkeeping, which remains in the parent's residual. Therefore exclusive is only observed-child-exclusive, not pure function body CPU or whole-program exclusive cost. The aggregate remains an observer with nonzero cost.

Synthetic test evidence and final source review can qualify this diagnostic implementation. They cannot qualify production behavior, prove the original lease passes or provide permission to run another business window. Existing historical total/codec metrics remain tied to their original observer and execution.

