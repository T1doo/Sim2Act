# Fixed composite parent pin — final closure review

2026-10-21. Independent read-only review. Result: **LIMITED_NATIVE_COMPOSITE_CODE_AND_LOCAL_EVIDENCE_ACK_NO_START_ACK**. The earlier design and initial code reports are retained as their original records; the initial truthiness P2 is closed in the exact bytes below. No new P1/P2 identified in this increment. Reviewer ran/imported no product/code/tests, opened no database, invoked no Worker/Mock/G0/commit and edited no repository files; only source/hash/log reads and /tmp report writes.

## Final exact SHA256

Current files were independently hashed twice and match `/tmp/sim2act-composite-parent-pin-20261021/closure-hashes.json`:

| File | SHA256 |
|---|---|
| `src/sim2act/cold_accounted.py` | `055c4634a86ef3aa14b8c702ee1396c5832eb9759d171eb963d31c2b4693f180` |
| `src/sim2act/natural_live_admission.py` | `d199b4dfc31f7a57ff9b00aacf7b40f820c98cad4aca0631b9f102cf8367c747` |
| `src/sim2act/natural_source_archives.py` | `2d0e99c18a33bcadd50410b9979b36c3b555e946f32c7fdbf3700b7c7524465c` |
| `tests/test_cold_accounted_stage_pin.py` | `d9ca95f656b6abd0f79625267025f22726f7bb63a4124028518f9ea96d4882ea` |

## P2 closure and implementation scope

The dispatcher now requires exact OwnedMode, exact NativeCandidate and `owned_ready is True`; the private `_pin_stage` uses the same literal-ready check after its original first pin. Neither new selection performs truth conversion on a substituted ready object. The new test replaces ready with ForeignBool, makes the original first pin raise an exact marker, and checks marker identity and no __bool__ call: precisely the ordering promised, without changing or overclaiming the old fallback's later behavior.

The earlier foreign-native and extraction issues are also closed: type(candidate) is exact before ready access, and the private Cold extraction branch requires exact tuple/length four before unpacking. The two targeted parent closures alone route through the helper. Defaults and nonnative modes retain `_graph_trial_pin` then self-pinning `_graph_trial_stage_raw`; Source proof identity remains immediately after the resolver parent pin.

The native composite starts with original `_graph_trial_pin` and its exact graph/store/connection/closed rejection behavior, then mode dynamic/header checks and links, followed by the same fixed stage relation sequence. Generate family/run, Source job or Cold binding/job/Source family, raw/metadata and extraction draft/target/goal predicates remain. Exact Family/Record and issued arena membership are retained; leaves still execute scope current/dynamic gates. Public assert_current/family/run/stage retain their old full-check paths and relation order. No general skip/current token, reentrant flag, cross-call cache or new authority exists. Any composite BaseException closes the mode and propagates. Typed cohorts, queries/external-return guards, ledger full-domain comparisons and final lease/transaction checks are unchanged.

This is a fixed parent-boundary consolidation. Local test evidence counts 7→1 original codec calls for one valid Source/Cold parent invocation, with equal family/run relation sequences. It does not establish whole-G0 timing, deadline success, full PB, production eligibility or a generally safe removal of other current checks. The nine-position stage shape is preserved; the frozen/body typed/model boundaries remain responsible for positions not independently compared by the old identity predicate.

## Closed-connection evidence handled explicitly

The earlier 98-case broadened batch remains **97 passed / 1 failed**, JUnit 163.856 seconds (pytest 163.86). Its preserved stack shows the new private path entering the original graph pin and producing DomainError/VERSION_CONFLICT for the closed connection. During unwind, existing `pb._source_reads` finally accesses c.info at line 570 and raises ResourceClosedError; Store.tx cleanup accesses c.info again and can replace it with another ResourceClosedError. Therefore the failed outer DomainError expectation was not proof that the pin had accepted a closed connection, and is not relabelled a passing full batch.

Final test splits this behavior: inner assertion checks the exact pin DomainError code and inactive mode/empty issued scope; outer assertion separately expects the pre-existing ResourceClosedError while unwinding the deliberately closed fixture. Production source-read/Store.tx cleanup is not changed or claimed repaired. This is a bounded test-harness distinction, not swallowing an unexpected product failure or a production cleanup success claim.

## Final local originals read

`closure-junit.xml` records **24 tests, 0 failures/errors/skips, 36.131 seconds**; closure pytest log reports 24 passed, one warning, 36.13 seconds. These are the final targeted cases including ready callback ordering and the explicit closed-connection body/finalizer distinction. They also cover Source/Cold relation damages, per-call frontier/write/revocation/transaction/stop drift, source receipt and complete Source Slot non-aid difference, typed-cohort mutation, post-query revocation, default order and exact two callsites. Source/consumer tests are local synthetic/helper contexts, not production Mock/G0 execution. The remaining 97 passing cases from the broader batch are earlier evidence, not a repeated final all-green 98-case run.

Closure mypy reports success for 3 source files; closure Ruff reports All checks passed. Reviewer read these author originals rather than executing verification.

Original SHA256:

- closure-hashes.json `b3e9b3ce39945d7bea7556fec3d4e1b036aeb071ccb5f90b0a4eeb8c425cb4de`
- closure-junit.xml `550a44d03e0cec5b30fadeba7ab725083fcb53bad4d087cd65dd0e4d6be6b281`
- closure-pytest.log `d976e61227a0db632e5122b42ce6680d73b8652c82b03061879ea6f0ea48df3e`
- closure-mypy.log `8228fcc5ce46d42d01caf3cd941f4e9c5f2bcc372bb5b147a2f0572d2dd675a8`
- closure-ruff.log `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`
- earlier final-junit.xml `4c164ecc89e99863c93376b970d42e7b2e789fb5cd50290e0057b651181816a0`
- earlier final-pytest.log `c81e91de2294bbba1b2dc97bf71d9cc14d6ad5f4684195060cec45f9664aaa37`

This report ACKs the frozen limited implementation and author local evidence. It creates no grant, authorizes no execution window/retry and makes no actual-G0 performance or qualification claim. Any future attempt requires its own authorized, frozen source/config/grant/protection conditions; this report is not a substitute for them.
