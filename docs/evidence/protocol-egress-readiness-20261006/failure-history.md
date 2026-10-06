# Preserved failures

2026-10-06: the first local HTTP/jobs run after narrowing the extraction scope to
one request returned **61 passed / 6 failed** in 22.79 seconds. The two HTTP full
chains and four jobs full-chain/tamper variants failed before extraction send with
`VERIFICATION_FAILED: Complete bounded source trace required`.

Cause: source history validation reused the current extraction request allowance
(one), while a legitimate independently reviewed source had two requests (read,
answer). Fix: preserve the one-request extraction send gate, and obtain the
source history bound separately from the authenticated frozen source scope.
Standalone ModelProtocol callers retain their previous default bound.

Post-fix HTTP/jobs/ModelProtocol run: **108 passed** in 39.01 seconds, with one
existing Starlette TestClient deprecation warning. This is local SQLite/mock
evidence; it does not replace native Windows or real-provider semantic tests.

The initial public-catalog test had an incorrect positional `create_app` call
(28 passed / 1 failed), then incorrectly expected missing authentication to
return 401. The existing API consistently returns 403 `PERMISSION_DENIED`.
The test now uses named arguments and checks the existing 403 behavior with no
catalog fields returned. No global authentication behavior was changed.

The next focused run returned **114 passed / 2 failed** in 31.82 seconds:
the authentication expectation was still loaded from the earlier test, and the
new pure-protocol fixture asserted its old global three-request scope against a
one-request extraction scope. FakeRunner now carries its explicitly supplied
test scope; actual provider authorization remains unchanged.

An in-progress whole-suite snapshot returned **788 passed / 34 skipped / 1 failed**
in 404.25 seconds (823 collected). Its new cold-handoff negative case placed the
entire source output into an instruction, exceeding the original 1500-character
candidate limit before it could reach the handoff oracle. The test now injects
the actual small source decision, which passes the ordinary candidate validator
and is rejected by the stricter handoff. Final frozen controller/budget/dry-run
focused validation returned **59 passed**; the earlier full failure is retained
in `working-tree-regression-failed.log`, not rewritten as a pass.

The handoff author also retained an initial 20-pass/1-fail public-resource metadata
expectation and 26-pass/1-fail oversized-instruction test, plus temporary lint/type
errors. These were implementation-stage checks, not final acceptance receipts.

Native Chromium startup returned a real FAIL: the installed SUID sandbox helper
is not configured with the root ownership/4755 mode Chromium requires. It aborts
under its default sandbox. The diagnostic is retained in
`native-chromium-failed.log`. No security-disabling flag or system permission
change was used. A precise subsequent environment skip is BLOCKED coverage,
not a successful browser test.

Two interim full runs each returned 794 passed/35 skipped while implementation files changed during execution. They are preserved as `ui-changing-full-regression.log` and `pre-role-guard-full.log`, not final frozen coverage. In the first, an older UI fixture lacked `other_run`, so its current-project negative inadvertently checked an undefined ID. The final fixture creates a real owned-other-project protocol Run; the driver strictly requires its valid ID before testing rejection. Final current-source HTTP DOM21 checks pass.

The final independent audit reproduced the baseline role defect: genuine cold contract goals/hashes were accepted as source despite independent holdout intent. Three layers now bind material role. The first role-focused run returned151 PASS/1 FAIL because an old positive test called all registered contracts source; its phase now follows the actual registered role, with four explicit opposite-role rejection tests retained. `role-positive-fixture-failed.log` preserves this result. Final role-focused run is152 PASS.

Final full regression is **799 PASS /35 SKIP /0 FAIL**, 365.72 seconds. All157 frozen source/test/script hashes are unchanged before/after. The exact full log and hash manifests are retained separately; no earlier failure was overwritten. Native Chromium remains blocked, and PostgreSQL-only tests were not activated.
