# Explicit Mock candidate wiring — frozen static code review

2026-10-21. Reviewer: independent_gap_review. Result: **LIMITED_STATIC_WIRING_ACK_DEFAULT_OFF_NO_START_ACK**. No additional P1/P2 found in the four frozen files. This review performed only source/diff/hash reads and wrote this report under /tmp: no product import, test, database, Worker, Mock, G0, full prepare, trial commit or prefix execution; no repository edits.

## Exact frozen files

These SHA256 values were independently computed from current files and equal `/tmp/sim2act-explicit-mock-wiring-20261021/frozen-hashes.json`:

| File | SHA256 |
|---|---|
| `src/sim2act/natural_spec_runtime.py` | `eb6010151979b5c6e085559f45e4a4fb430db3790393d44162a8e3e4d924c459` |
| `scripts/diagnostics/g0_guard.py` | `07d001a11c3d3300c2873bacfaaf40ec67c4ae3194801371dc3d6e34129651ab` |
| `scripts/diagnostics/g0_prefix.py` | `c67132016a0c782d148aeae8ca6ab2c164ba78182d984d46dde99682e116596b` |
| `tests/test_cold_accounted_mock_wiring.py` | `fd1071ba378104a6083a912492f424f2fddd1ec7adc64b69e418051cc8411a38` |

## Reviewed behavior

`natural_spec_runtime.py:3042` introduces only keyword-only `_mock_accounted_config=None`. Non-None requires exact `_NativeConfig`, test-only SQLite and the original eligibility gate before entering the graph. An explicit ineligible request rejects; the None branch retains original ineligible `yield None`. Original roles and first binding retain their position. The candidate context enters inside the original pre CGR after first binding and receives that exact guard; only this branch passes candidate to the trial constructor. The constructor additionally requires synthetic SQLite/pre, while retaining exact candidate identity, same graph, no prewrite mode and unissued result (`:2457`).

The inner ExitStack encloses the yielded trial and unchanged original second-complete authority-record and finite-deadline checks. It unwinds before original `_cold_graph_read` final check/invalidation. The original final stop/time check remains after both scopes. Existing candidate helper propagates BaseException and closes on exceptional unwind; normal owned closure remains with the original graph final check/invalidate. No new swallow/fallback is added. The empty default stack changes no application checks or result selection; this static review makes no timing equivalence claim.

`g0_prefix.py:8` returns the original callable for None and exact-config partial only for explicit config. `run_prefix` retains original_context separately and passes selected_context only through `_target_context`. `g0_guard.py:423` leaves unbound/non-target calls on original without keyword config. Original target/current/version/attempt checks, Mock budget close, entered/notify/arm and timer order are unchanged. The selected context is entered only inside the target's original protected try, and the existing rejection/success handling still sees its full unwind. This closes the initial global-partial P2 without weakening runtime explicit eligibility.

Repository source search confirms the ordinary runtime caller still passes no keyword (`natural_spec_runtime.py:3667`), the post constructor remains `audit_seed` only (`:3337`), and the existing bounded launcher still calls `run_prefix` without any keyword (`g0_bounded.py:229`). This patch adds no environment/public configuration, grant, default activation, account evidence or account/qualification substitution. The original three configured fixture substitutions remain a separate visible test boundary; this option cannot supply production eligibility or prove that a production account can reach Source/Generate.

## Test scope, read rather than executed

The test file contains 11 expanded local cases: selected/default exception-unwind (2), absent second guard (1), normal/expired record-shaped local closure (2), non-synthetic store rejection (3), wrong config/route/default yield (1), prefix selector and unchanged default/post-call AST contracts (1), and pure target-only boundary routing (1).

These tests use real CGR/native context for lifecycle but replace first binding and TrialGraph with stand-ins. The locally inserted authority-record-shaped value is explicitly a closure harness, not a completed business proof. The pure boundary case seeds synthetic MockBudget counters and uses a stand-in arm callback; it executes neither actual exchanges nor a real G0. No test in this file calls full `_prepare` or commit. The final run of these 11 cases was pending when this report was written; no pass count is independently attested here. Author-provided earlier 9-case results are not promoted to results for this final file.

## Remaining qualification boundary

This acknowledges only frozen source wiring and closure of the reported target-routing defect. It does not establish full Source/Generate candidate selection through actual prepare, issued arena lifecycle through both complete guards, performance, deadline success, production/account permission, full PB, G0 success or permission for any new Mock/G0 window. Future execution would require its separately reviewed exact mode/config, source/grant binding and existing protection/budget conditions. Current default launcher remains unselected.
