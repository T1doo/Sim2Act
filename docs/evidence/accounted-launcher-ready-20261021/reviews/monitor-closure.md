# Launcher profile closure: independent incremental review

Decision: **ACK_FINAL_PREPARATION_CODE_ONLY**. The ordinary observation-failure isolation gap is closed in the reviewed implementation. No new blocking issue was found within the preparation, finite-profile, protection and reporting scope. This does not authorize a grant/window or establish complete-input OWNED eligibility, full G0 acceptance, performance, RSS or real production qualification.

Scope: read-only final seven files/diff, hash manifests and writer-produced closure logs/JUnit/checks. No code, tests, DB, product/Worker/Mock/model, G0, prepare/commit, profiling or signals were executed by this reviewer. No repository files were changed; only these `/tmp` closure reports were written. Base HEAD: `09b58a414a6db0665de759ff77dfb51bb2b735b7` with the reviewed patch. Earlier design/code reports remain preserved.

## Observation failures no longer control ordinary outcomes

- Native phase/route/reason/budget construction runs through `observe`, which catches ordinary `Exception` faults and marks diagnostic evidence incomplete. It does not select a route, consume fuel, validate facts or alter an existing selection result. The original pre-issuance LEGACY result and original capacity/current-data checks continue even if budget recording fails.
- `selection_record` also fails conservatively to UNKNOWN/incomplete evidence when scalar collection fails. The original error path uses nested `finally` so mode and ledger cleanup are attempted even if observation fails. Newly added local regression covers OWNED and LEGACY budget-observation failure, and original DomainError identity plus ledger closure when error observation fails.
- The commit wrapper attempts its bounded record setup separately, calls the original commit exactly once, and preserves its returned object or reraised error. Ordinary output/deadline-read or record-append failure only invalidates the trace. It does not replace a successful return with metadata failure or conceal a body error. Final report construction has a bounded incomplete fallback.
- Original scope-returned is still set only after the real original context returns through final graph/stop/clock checks. A metadata failure cannot manufacture that event. Candidate report completeness requires both actual commit returns, valid original deadline evidence and non-incomplete diagnostics.
- The parent now additionally requires `diagnostic_incomplete is False`. Incomplete or UNKNOWN metadata cannot be accepted as candidate completion. The existing distinction between complete OWNED, separately labeled complete LEGACY and UNKNOWN remains intact.

This isolation claim concerns ordinary recording `Exception` failures. It is not a promise to continue through process termination or arbitrary control `BaseException`; existing graph/ledger `finally` boundaries remain the cleanup mechanism for such exits. No hot-path IO, extra graph scan/hash/pin, DB query, consumer replay or business guard was added.

## Unchanged limits, route and eligibility

The finite profile is unchanged: bounds60000/120000/128/8 MiB/64 MiB; logical resident512 MiB, peak1 GiB, integer_bits16000 and work twice the joint-two-packet quartic classify upper. It remains explicit, canonical-hashed and scope-bound in the description/exact grant. It does not guarantee OWNED, all complete input fit, CPU or RSS; maximal arena counts still need not fit the resident cap.

The protection/selection design remains as independently reviewed: default None, exact private profile and same pre guard, candidate after original first binding, original two producer positions and commits, no post selection, no account/software bypass, fixed historical three synthetic fixture gate replacements. A candidate CLI flag does not constitute permission to execute; wrong profile/grant/runtime/protection conditions refuse.

Guard implementation, native budget implementation and runtime wiring hashes are unchanged. Existing source diff also confirms account/environment/software and configured fixture files unchanged. Original six exchanges/eight methods/two Source delegates, lease30/per-Run300/TTL1800/60-second pacing, 480-prefix/120-G0/600-work+10-cleanup and sampled64 MiB directory policy remain. Parent sampling still uses each supervisor iteration/finalization with selector cap0.05 seconds; no native hard quota, periodic0.1-second scheduling or whole-process-memory claim was introduced.

The required VFS-independent same-interpreter child-I/O/raw-alias units remain in place. Their positive/denial/terminal-child scope is unchanged, and the four old optional VFS-dependent skips stay skipped. No interpreter/SQLite API substitution or new real network/model path was introduced by this closure.

## Writer-run evidence and exact hash qualification

- Closure pytest log: **131 passed**, one existing Starlette warning, **95.99 seconds**. JUnit independently states 131 tests, 0 failures/errors/skips, **95.991 seconds**. These are local/component/real synthetic SQLite tests with execution tripwires, not full native prepare/commit/G0 or Mock acceptance.
- Closure guards: **33 total = 29 passed + 4 existing optional VFS skips**, **0.157 seconds**.
- Closure mypy: no issues in two source files. Closure Ruff initially reported exactly one I001 import-order finding in the newly extended test; that log is retained. Final Ruff is **All checks passed**.
- All seven actual final file hashes match `final-hashes.json`. The closure-test manifest matches six of these exactly; its new-test hash is `9389cfcafcdab22d987ab5834dc966da560482cd14b7c734025c6bb91f290e25`, whereas the final sorted-test hash is listed below. The writer reports only Ruff import sorting afterward; the retained I001 excerpt and inspected final imports are consistent with that narrow change. This report does not relabel the 131-run as a byte-identical run of the final seventh test file or require a redundant suite rerun.

These results close the local ordinary-observer-failure regressions. Actual original full-input fit, OWNED selection and both complete native commits under the profile remain empirical conditions for a separately approved future window. No such window or grant was created or approved by this review.

## Final seven SHA256

| File | SHA256 |
| --- | --- |
| src/sim2act/_cold_accounted_native.py | 85e493b32ce1bd80824652e08e93ab484c6e6137999b0ec622db0083823aea76 |
| src/sim2act/cold_accounted.py | c8afddb4aedb0b651e2797aa9d9c59356abd2b169a27e7cf749bf8fbde02b427 |
| scripts/diagnostics/g0_bounded.py | 15999ea969ebc6729d96852108bef956649592d92dc4c9a9decf089006889760 |
| scripts/diagnostics/g0_prefix.py | b42a5e104ee595f1633414a84a8e90c44788e1b6f06a45c5eb8f8df28680d5c9 |
| scripts/diagnostics/test_g0_guard.py | dc9c1634a5c71ead3e1ea48e1fd4f8c34e5e3441bb1cb22cf942d2b4f355bb1d |
| tests/test_cold_accounted_mock_wiring.py | f29cf24ea5bed295f78bdd7c862d3555f616ce22a0b85f0c602403eb7c0fdbf9 |
| tests/test_cold_accounted_launcher_ready.py | 97bd58d348c8f1e4a27e170192e1d72338f1275af6f7d7f739db478bcff0deb0 |
