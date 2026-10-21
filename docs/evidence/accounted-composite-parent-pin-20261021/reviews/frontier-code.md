# Fixed composite parent pin — initial frozen code review

2026-10-21. Read-only independent review. Result: **P2_READY_DISPATCH_TRUTHINESS_ORDER_FIX_REQUIRED**. This initial report binds the four hashes below; later source/test corrections need a separately recorded closure review. No product/code import, tests, database, Worker, Mock, G0 or commit execution and no repository edits were performed by reviewer.

## Exact files read

Current SHA256 values matched `/tmp/sim2act-composite-parent-pin-20261021/final-hashes.json` at review:

| File | SHA256 |
|---|---|
| `src/sim2act/cold_accounted.py` | `1cdaba2383ed719787b0871a530bf4091ce195259ed4efaf9afa20816e764043` |
| `src/sim2act/natural_live_admission.py` | `038cab392a0a435f987b1f0672b3141e0a17712126efefd4a316632b265889f0` |
| `src/sim2act/natural_source_archives.py` | `2d0e99c18a33bcadd50410b9979b36c3b555e946f32c7fdbf3700b7c7524465c` |
| `tests/test_cold_accounted_stage_pin.py` | `cf5ed61e544bcefd6fe0bc78cd327f21c2161e584c075074f978777ec444a8f7` |

## Remaining P2

The new dispatcher checks exact OwnedMode and NativeCandidate before native.owned_ready, closing the foreign-native property issue. However its final `and native.owned_ready` performs truth conversion before the original first `_graph_trial_pin`. The exact candidate's private flag is a writable attribute; if it contains an object with __bool__, this new dispatch executes that callback earlier than the original first-pin boundary. Use `owned_ready is True` at the dispatcher and the private `_pin_stage` qualification. This binds the new route to the intended literal ready state without a new callback.

The required preservation is specifically no NEW truth-conversion callback before original first pin. The fallback retains the old path and its old dynamic behavior; this review does not require changing legacy `_dynamic` or eliminating every callback that old invalid state could reach later. A test can verify first-pin-before-callback ordering or private `_pin_stage` exact-ready refusal; it should not invent a stronger legacy-wide no-callback requirement.

## Reviewed implementation otherwise

Only the two intended local parent closures call the new helper: graph_run_context and graph_resolve_trial_source. Default and nonnative paths retain original `_graph_trial_pin` then `_graph_trial_stage_raw`, including keyword selection. Source-proof identity remains after parent pin in resolver. Typed cohort, query/external-return checks, and final admission/deadline/transaction SQL are not changed by the diff.

Private `_pin_stage` now starts with the original gate._graph_trial_pin, preserving original exact graph/store/connection and closed-connection refusal order before pure mode associations. It then checks exact candidate/native readiness, dynamic header/current state and issued links; original one complete CGR/frontier serialization remains. The pure relationship sequence matches old stage assertions: Generate family twice (direct assertion and former public run's family assertion), Generate Run, raw/metadata identities, then Source family/Run or Cold job/binding/Source family and extraction draft/target/goal identities. Exact tuple length-four extraction gate closes the earlier foreign iterator issue. Any composite BaseException closes the mode then re-raises.

Public assert_family and assert_run only delegate their unchanged relation bodies to private methods after their original current/family calls; public assert_current and assert_stage paths retain their original complete-check calls and order. Family._root/Value leaves still execute scope._current/_dynamic and exact issued/arena checks. There is no generic skip flag, reentrant/current token, validation cache or exported authority. Nine-position stage shape is retained; existing frozen/body typed boundaries, not this identity predicate alone, protect the positions not independently compared here.

## Test source and pending evidence

Read 23 expanded targeted cases covering valid Source/Cold old/new local codec counts and associations, 11 relation damages, 6 current/mutation/transaction/stop cases, foreign native/extraction callbacks, default order/two callsites, real local source receipt/full Slot difference, typed cohort drift and post-query revocation. The local 7→1 codec assertion concerns one fixed parent invocation only, not measured G0 improvement. Reviewer did not execute these cases.

The author reports the first 21-case development round had 19P/2F, and that a later real c.close test still encounters ResourceClosedError from pb._source_reads finally during fixture teardown, which can replace the pin body's DomainError. This known fixture-exit distinction is not treated as a passed final case or a reason to modify production transaction/cleanup code. Author will preserve failed originals and refine the test to distinguish body refusal and teardown. Final test hash/results are pending and are not attested here.

This initial report gives no frozen final code ACK, performance claim, grant or execution-window permission.
