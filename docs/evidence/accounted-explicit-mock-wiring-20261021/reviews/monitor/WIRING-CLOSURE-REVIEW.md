# Explicit Mock wiring closure: independent static and evidence review

Decision: **ACK_DEFAULT_OFF_EXPLICIT_SYNTHETIC_WIRING_ONLY**. The previously reported selected-context error classification gap is closed in this four-file freeze. No new code-review blocker was found within this narrow wiring scope. The pre-fix `WIRING-CODE-REVIEW.md/json` remain unchanged as historical review records.

Scope: read-only actual source/diff, final hashes, writer-produced local test log/JUnit, guard-unit log, Ruff and existing mypy log. This reviewer did not execute tests, product code, DB, Worker, Mock/model, G0, prepare/commit, profiling or signals; no repository edits or new execution windows. Only these `/tmp` closure artifacts were written. Base HEAD remains `a0fbd16e7d917ca00ab55aed81519d454bb35998` with the reviewed working-tree patch.

## Classification closure

`StopBoundary.wrap` now labels any DomainError on an explicitly selected target context **UNKNOWN**, recording `error_origin=UNDETERMINED_ORIGINAL_OR_CANDIDATE`. It does not guess whether the original business guards or the new candidate caused it. The top-level saved error/diagnostic fields become `selected_context_error` and `selected_context_diagnostic`; the same exception object is retained in `G0Stop.original` and as its cause. This internal historical attribute name does not establish original-guard provenance. Unrelated errors still follow the existing unknown/error path and protection denial cannot be relabeled as a business refusal.

For `_target_context is None`, the original `G0_ORIGINAL_REJECTION_NO_W5` classification and `original_error`/`original_diagnostic` fields remain. The pure local boundary regression now covers both an ordinary body DomainError and `_Capacity`, asserting UNKNOWN, undetermined provenance, retained exception identity and absence of the top-level `original_error` field. The unchanged parent launcher accepts only original-rejection/completed classifications as finished known outcomes; it therefore refuses UNKNOWN as a successful diagnostic and retains UNKNOWN. No CLI/grant whitelist is widened.

## Wiring and boundary conclusions retained

The runtime/prefix hashes did not change during this closure. Selection remains default None; exact private config plus test-only SQLite and the original exact PB Cold route are required for an explicit request. The prefix constructs a partial of the captured original function rather than a replacement business implementation. The selected context is invoked only for the exact bound target after the original worker/run/call/version/attempt, exact Mock counter closure and SQLite arm checks; non-target and unbound calls always invoke the original context.

Candidate entry remains on the same pre guard after successful original first binding. The actual constructor receives the candidate. Original complete second-authority identity/finite checks remain; candidate context exit precedes original graph final check/invalidation and the final clock/stop check. Default `advance_model` and post/audit constructor remain unselected. Launcher, original three disclosed configured fixture gate replacements, account resolver, production environment/software gates and every existing protection budget remain unchanged.

This is a dormant explicit synthetic seam, not an installed production optimization. It neither invokes a new window nor changes the existing grant. The exact six exchanges/eight methods (two Source delegates), at-least-300-second reservation span, TTL1800/per-Run300/lease30, 480-prefix/120-G0/600-work+10-cleanup and 64 MiB sampled directory budget conclusions remain as in the companion design review. Native finite full-input allowance/OWNED eligibility and whole-process RSS are not proven by fixture values or by this wiring patch. No whole constructor/prepare/two-commit/G0 performance or deadline result is claimed.

## Final evidence actually inspected

- `closure-pytest.log`: **12 passed**, one existing Starlette warning, **2.73 seconds**. JUnit independently states 12 tests, 0 failures/errors/skips, 2.727 seconds. These are writer-run local wiring tests using disclosed first-binding/TrialGraph/record-shaped stand-ins; they are not complete business proofs or a Mock/G0 acceptance run.
- `closure-guard-units.log`: **31 total, 27 passed and 4 skipped**, 0.094 seconds. The skips are the existing separately compiled native-unit dependency; they are not new passes or proof of a native hard quota. The unchanged original None-path refusal/exception preservation and complete-context stop units are included.
- `closure-ruff.log`: All checks passed. The existing mypy log reports no issues in one source file; runtime is unchanged from its reviewed hash during classification closure.
- Earlier `frozen-pytest.log` records **192 passed / 59.58 seconds before the classification change**. It is preserved as earlier evidence and is not relabeled as the final four-SHA regression. No enlarged repeat was performed or requested by this reviewer.

This ACK does not approve a fourth execution window, a new finite config, real credentials/account source, production installation, unrelated guard removal or any claimed G0 speedup. A future explicit execution would still need its own authorized reviewed grant/config, actual selected OWNED/LEGACY evidence and complete original-path results.

## Final frozen SHA256

| File | SHA256 |
| --- | --- |
| src/sim2act/natural_spec_runtime.py | eb6010151979b5c6e085559f45e4a4fb430db3790393d44162a8e3e4d924c459 |
| scripts/diagnostics/g0_guard.py | 812a01a06ebb2694d68d50c3a02fd08c8266772cf036a54b0e364e0f9bfe5812 |
| scripts/diagnostics/g0_prefix.py | c67132016a0c782d148aeae8ca6ab2c164ba78182d984d46dde99682e116596b |
| tests/test_cold_accounted_mock_wiring.py | 7e834a927f87e4036d985529e3e4ae0e7a90500b0e23b8bb0e574e5c90c83af2 |

All four actual files matched `closure-hashes.json`. The companion JSON binds the final evidence bytes inspected.
