# Historical correction evidence: bounded read-only review

This review read selected tar members into memory; it did not unpack the archive, read any database member, run a product test, use Git/network, or read private holdouts. Exact member hashes, input-map comparisons, function AST comparisons and XML results are in `archive-reuse-verification.json`.

The historical execution is not current-source qualification. Its product freeze was `2e21d0fbfa810f5f117523e6e74412df6bd033a7`, with test-only head `357264c20c42fa5bc3ddf6afc1d8d4f4a2c70fe7`. The selected final matrix has 456 unchanged execution inputs; its 99 product source entries equal the product-freeze map. The new correction-result button did not exist there.

Archive: `docs/evidence/natural-spec-correction-20261013/natural-spec-correction-evidence-20261013.tar.gz`.

`author/formatted-final-matrix.xml`, SHA-256 `384749c14b50b035552cc426282d5cfb6913d4b2d050d451345a167960789d20`, contains 17 named PASS nodes. The command and completed result are `author/formatted-final-matrix-command.json` and `author/formatted-final-matrix-result.json` (exit 0, 530.997449398 s). Relevant nodes use classname `natural-spec-correction-evidence-20261013.author.seeded_cases`:

| Historical node | Result | Actual scope retained in its test |
| --- | --- | --- |
| `test_explicit_rejection_to_actual_new_result_and_fresh_owner[pa]` | PASS | Explicit correction, actual synthetic-model Worker result v2, unchanged Goal/criteria, new owner sequence 0/PENDING, independent simulated DECIDE. |
| Same node `[pb]` | PASS | Same bounded contract for historical P-B. |
| `test_preconfirm_invalid_source_no_partial_run[revoke]` | PASS | Real fixture resource Grant revocation before commit, 403/409, exact whole snapshot unchanged, prior request ABSENT. |
| Same node `[goal]`, `[expired]`, `[wrong-fp]`, `[withdraw]` | PASS each | Goal version change, controlled expiry, wrong fingerprint and declaration withdrawal; the expiry clock is explicitly patched in this historical test. |
| `test_withdraw_after_queue_prevents_worker_result` | PASS | Parent declaration withdrawn after queue; no model send, child FAILED, original single typed version retained. |
| `test_cancelled_correction_keeps_original_result` | PASS | Cancelled correction preserves the original result. |
| `test_late_model_reply_after_declaration_withdrawal_cannot_commit` | PASS | Late actual Mock response after declaration withdrawal cannot commit. This is declaration withdrawal, not a claim that every source-Grant/cancellation race was executed. |
| `test_original_worker_proof_pollution_stops_correction[binding]`, `[attempt]`, `[receipt]` | PASS each | Historical parent binding, Attempt or receipt pollution stops the queued correction without a send. |
| `test_visible_rejection_correction_and_independent_owner[pa-normal]`, `[pb-run-lost]` | PASS each | Historical visible actual-HTTP/JSDOM and Worker chain. These nodes precede the new direct-result button. |

The source test `source-final/tests/test_natural_spec_corrections.py` is byte-identical to the current tracked test (SHA-256 `bc554c890885add3dfcfde3fc2c6fd72c29516568f4a0df6046a658502cf6abe`). Its successful correction checks preserve every prior typed/owner/seal row and the old AppRun, then verify the new owner separately. The old matrix ran its seeded wrapper; its command member identifies that execution exactly.

UI delayed-scope evidence is separate controlled evidence. `independent-ui/final-2e21/controlled-final.xml` (SHA-256 `3b7a923bb1996fdf239d18d6d51851f6d177d99bba83f2b1dda8e89c515640e2`) has `recover-poison` PASS and `late-scope-and-hash` PASS, alongside `lost-submit-failed-get` FAIL. The latter later passed in `controlled-lost-rerun.xml` (SHA-256 `0935eef062bc2aa6144d5d758f6c916cc6441fd83c3737570cc3f5f2a7d25cac`). Proof members retain original-key GET-only recovery, newer pending intent preservation and prepare-hash late-navigation fencing. Their own classification is `CONTROLLED_CURRENT_ASSET_JSDOM_VM_NOT_FULL_VISIBLE_USER_FLOW`, with no new Worker or model execution. The failure remains part of the evidence.

Current-source limitations: correction `approve/bound/feedback/gate/mount/preview`, owner natural review paths, `natural_spec_runtime.advance_model`, `pa_spec_apps` validation/commit paths and Worker class methods have changed. In particular Worker `__init__/finish/once/process/reserve` differ, although `main/attempt_parameters/checkpoint` are unchanged. Thus matching test bytes or matching four JS handlers cannot bridge all current runtime dependencies. The archive's `correctionValidate`, prepare, submit and recovery handler byte ranges match current source; the new button and navigation are additional code. The archive can support historical contract evidence, not a current-source blanket PASS or the new button's actual-Worker qualification.

The current fresh attempt's actual failure and retained backend responses are recorded separately in `first-http-failure-review.json`; it is not rewritten as PASS. No Windows/native browser, PostgreSQL, real model, real human semantic acceptance, CI or full F2 qualification is inferred.
