# Internal Mock candidate wiring — design review

2026-10-21. Read-only source review by independent_gap_review. No product import, test, database access, Worker, Mock, G0, prepare or commit execution. No repository writes. This is a design review, not a frozen-patch or runtime ACK and not permission to start a window.

## Result

Runtime internal wiring is conditionally acceptable with the ordering below. The proposed globally selected prefix `partial(original, _mock_accounted_config=config)` has a P2 integration defect and needs a target-only selection boundary before static acceptance of that part.

## Runtime ordering and invariants

1. `None` preserves original eligibility and its ineligible `yield None`. Explicit non-None selection requires exact `_NativeConfig`, test-only SQLite and the original `_cold_model_eligible`; ineligible explicit requests reject, never silently fall back.
2. Preserve original roles, pre `_cold_graph_read`, and `_cold_first_binding`. Enter `_native_candidate` only after that original binding, passing the same guard to `_ColdTrialGraph`.
3. Place the candidate ExitStack inside the original graph context. It must enclose the yielded trial and the original second-complete-record / finite-deadline checks, then exit before the graph's final original `guard.check()` / invalidation. Keep the final stop/time test outside both contexts. Calling candidate `assert_current()` after graph invalidation would break lifecycle ordering.
4. Constructor candidate checks retain exact candidate/graph ownership, no prewrite mode, unissued result and pre phase; require test-only SQLite explicitly. Post construction stays without candidate. Preserve original failure invalidation and BaseException propagation; no exception-to-default fallback.
5. No Source/Generate invocation is added at context construction. Their original `_prepare` producer and admission positions remain unchanged. This option does not satisfy account evidence or production-environment qualification.

## P2: globally selected partial also reaches non-target prefix contexts

`scripts/diagnostics/g0_guard.py:423` `StopBoundary.wrap` calls its supplied original context even while `target is None` or the worker differs from target (lines 425–429). `g0_prefix.run_prefix` installs that wrapper before Generate and Source and binds the Cold target only near line 271 in the unmodified prefix. The shared runtime caller invokes `_cold_model_before` for model contexts generally (`natural_spec_runtime.py`, original caller around line 3646; current working copy around line 3667).

Consequently, passing a configured partial globally supplies explicit config to those deliberately ineligible non-Cold contexts; the correctly strict runtime rejects them before the target. Do not fix this by weakening explicit eligibility.

Minimal correction: keep non-target calls on the exact original callable with no config; apply the selector only on the Cold target branch after the existing target/current/version/attempt checks, retaining all original StopBoundary protection and context-unwind order. A target-specific context argument or equally narrow existing-wrapper dispatch can do this. Do not invent new accounts, approval substitutions or infer a target from an ordinary unverified current record.

## Local verification scope to require of author

Verify default callable identity and untouched ineligible yield; invalid config/store/phase/eligibility fail closed; non-target Generate/Source routing stays unconfigured; verified target receives the same config and guard; constructor / yielded-body / second-record failures unwind without swallowing; successful candidate exit precedes the original graph final check/invalidation and post-close clock check. Harness/real-CGR lifecycle tests establish wiring only. They cannot establish full `_prepare`, G0 performance, expiry success or a new execution grant. Existing bounded launcher call remains without the new keyword and old grants cannot select it.

## Source inspection boundary

Original source was read at HEAD 824dfed3e9294727fd05aa88140d66b58b60ba3b. During this design review the unique author advanced HEAD to a0fbd16e7d917ca00ab55aed81519d454bb35998 and began an uncommitted runtime/prefix implementation. The observed draft runtime uses the required inner ExitStack ordering. The observed draft prefix still selects the partial globally. No exact implementation hash is approved by this design report; frozen-source review remains separate.
