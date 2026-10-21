# Composite parent pin: limited closure ACK

**ACK for this frozen, default-off native composite code change and its targeted local evidence. No remaining blocking finding was identified within the reviewed scope.** This is not a G0 outcome, lease/performance acceptance, native input-capacity qualification, or an execution grant.

The reviewer read the final diff, source, tests, hash manifests and author-generated raw logs/JUnit. The reviewer ran no tests, product, DB access, Mock/model, G0, prepare/commit, profile or signals; created no grant/window; and wrote only these review files under `/tmp`. Test results below belong to the author.

Base HEAD: `7832d211c6b952c6e79444c7f9bf666cc609fce4`. The actual four-file hashes were independently read with `sha256sum` and match `closure-hashes.json`:

| Frozen file | SHA-256 |
| --- | --- |
| src/sim2act/cold_accounted.py | 055c4634a86ef3aa14b8c702ee1396c5832eb9759d171eb963d31c2b4693f180 |
| src/sim2act/natural_live_admission.py | d199b4dfc31f7a57ff9b00aacf7b40f820c98cad4aca0631b9f102cf8367c747 |
| src/sim2act/natural_source_archives.py | 2d0e99c18a33bcadd50410b9979b36c3b555e946f32c7fdbf3700b7c7524465c |
| tests/test_cold_accounted_stage_pin.py | d9ca95f656b6abd0f79625267025f22726f7bb63a4124028518f9ea96d4882ea |

The ready-native branch is restricted by exact `_OwnedPrewriteMode`, exact `_NativeCandidate`, and `owned_ready is True`. The two changed call sites are only `_graph_run_context` and the Source archive resolver's parent pin. `_graph_stage_current` remains on its original sequence. Default/non-native dispatch still invokes the original full pin followed by stage validation.

The private composite first invokes the original `_graph_trial_pin`, preserving exact graph/connection rejection before inspecting stage facts. It then performs the existing dynamic/lifecycle and cross-family link checks and all original stage/family/Run joins. The extracted family and Run predicates remain in their public self-checking callers. Source-proof identity remains immediately after the resolver's parent call. The controlled cold extraction tuple barrier matches the existing exact tuple-of-four stage requirement; the default path is unchanged. Any composite exception closes the owned scope and re-raises.

The saved work is repeated full frontier encoding within this one lexical, pure-association segment. Each later invocation still makes a fresh full pin; there is no persistent pass token, cache of a mutable full scan, global/reentrant skip, or relaxation across query/callback boundaries. Family leaf access retains scope/frame/dynamic checks. Typed cohort guards, original SQL and external-return guards, authorization/revocation, fence, stop, transaction, and final deadline gates remain in place. The diff does not change launcher/profile/grant/resource limits, codec implementation, or the eligibility restriction to test-only SQLite.

The author closure log records **24 passed**, one existing deprecation warning, 36.13 seconds. JUnit independently records 24 tests, zero failures/errors/skips, 36.131 seconds. The author Ruff log reports all checks passed and mypy reports no issues in three source files. The targeted tests cover same-call codec count and retained family/Run predicates, 11 relation counterexamples, repeated-call mutation/revocation/write/rollback/stop, closed-connection refusal and scope closure, readiness callback order, foreign nested values, the two call sites and default order, real local SQLite Source receipt/whole-Slot equality, typed mutation, and post-query revocation.

The codec-count example is **7 to 1 in the tested local boundary**, not a sevenfold speedup or an end-to-end timing result. These tests use isolated synthetic SQLite lower-helper facts; they do not execute native constructor-to-prepare-to-two-commit, a Worker, Mock, W5, or a complete G0.

Earlier evidence is retained without upgrading its result: the initial run was 19 passed / 2 failed; the broad run was **97 passed / 1 failed**, 98 total, 163.86 seconds. The final targeted run does not turn that historical broad batch into 98 passed or imply that the broad batch was rerun under the closure hashes. Its remaining close case exposed existing fixture finalization replacing an already-correct `VERSION_CONFLICT` refusal with `ResourceClosedError`. The final test asserts those inner and outer outcomes separately. No production cleanup was changed or represented as fixed.

The next single six-exchange/eight-entry bounded validation remains the parent's separate user-authorized operation after freeze/push and an exact consumed-once grant. This ACK does not execute or expand it. All prior deadlines, disk monitoring, cleanup, error classification and uncertainty rules remain applicable; no new G0 success, two-commit completion or final deadline is established by this review.

Evidence under `/tmp/sim2act-composite-parent-pin-20261021/`:

| File | SHA-256 |
| --- | --- |
| closure-hashes.json | b3e9b3ce39945d7bea7556fec3d4e1b036aeb071ccb5f90b0a4eeb8c425cb4de |
| closure-pytest.log | d976e61227a0db632e5122b42ce6680d73b8652c82b03061879ea6f0ea48df3e |
| closure-junit.xml | 550a44d03e0cec5b30fadeba7ab725083fcb53bad4d087cd65dd0e4d6be6b281 |
| closure-mypy.log | 8228fcc5ce46d42d01caf3cd941f4e9c5f2bcc372bb5b147a2f0572d2dd675a8 |
| closure-ruff.log | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
