# Final optional ASAN loader: result and limitation addendum

**Non-blocking for the already recorded release-build synthetic candidate A/B; final ASAN qualified-loader selection is not verified and currently fails closed in the observed environment.** This supplements both final ACKs and preserves the new failed result. No code changes or additional run are requested by this conclusion.

Read-only review of `final-pinned-asan.log` and XML confirms **12 setup errors / 0 test-body passes / 2.43s** (JUnit 2.428s). Every recorded error is the selected fixture assertion `load_candidate(backend.__file__) is not None`, where the result is actually None. This is an optional tool-loader rejection, not evidence of a C memory-access error or a successful final ASAN test suite. The earlier 44-pass ASAN run predates the final loader gate; it remains evidence about the same C implementation under that earlier loader, and must not be presented as a passing test of the final loader.

The frozen adapter is unchanged, SHA256 `f356060885d0ab74edf7817732d72e69d54ff55d4a76b94d14df56f268fabd05`. Its ASAN-only branch requires the literal `/usr/lib/gcc/x86_64-linux-gnu/14/libasan.so` to occur in `/proc/self/maps`. The reviewer's read-only `readlink -f` resolves that installed path to `/usr/lib/x86_64-linux-gnu/libasan.so.8.0.0`, consistent with the author's reported actual mapping and false-negative diagnosis. The error log itself records the returned None, not an instrumented trace pinpointing the selected loader predicate. The static branch and reported mapping support the diagnosis without claiming an independently replayed proof.

That condition is short-circuited entirely for a release receipt with `sanitizer=None`. The final release 12-case qualification run and complete frozen release A/B already succeeded with this same adapter and release binary. The new result therefore does not contradict their recorded assertions or introduce a release-path execution blocker. A caller must treat an absent handle as no candidate and retain the default Python route; passing an unverified handle or silently weakening other gates is not justified. A future correction of the optional ASAN mapping check would be a new loader revision needing focused validation, not grounds to retroactively relabel this failed result or automatically repeat the release A/B.

The test log shows the raw `backend` fixture had already imported the ASAN extension before the selected fixture called the loader. Accordingly the precise scope is: the final qualified handle was not obtained, and these 12 selected test bodies did not run. It would overstate the evidence to describe this pytest process as having executed no native module initialization at all.

The independent binary digest pin, exact-build/layout qualification, original-frame stack probe and release runtime route are unchanged. This addendum makes no ASAN/LSan safety claim, no new production qualification and no G0 success claim. Reviewer product/test/DB/Mock execution and repository edits/signals remain **0**.

Original SHA256:

* `final-pinned-asan.log`: `f356cbf1e008f9b7e670aa24d39782b91826d87f7cb96ab60b2900e89f48705e`
* `final-pinned-asan.xml`: `94babe87672e5884e74034ad35272a434b7cb276e1becde2df7be2e35b214283`
