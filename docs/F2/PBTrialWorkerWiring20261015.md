# P-B same-Worker wiring candidate — 2026-10-15 — NOT_ACCEPTED

P-B extraction/Cold wiring is implemented and independently statically reviewed, but is **not accepted**. The initial Cold normal case failed before a new Attempt and all five Cold fault injections were unexecuted. Two later frozen-candidate runs failed in their shared Generate/Source prefix, before the Cold flow or fourteen source-proof counterexamples. No successful seven-slot P-B execution or verified lease/lock fix is claimed.

## Implementation and finite contract

Baseline is protected P-A `60534d3d554aa611d4d7c86da635c51a24ac7c92`. The independent development branch is `dev/pb-production-wiring-20261015`. `PATrialBinding` accepts only exact original P-A/P-B contract types in explicit test-only SQLite/MockTransport. Original Worker, captured InternModel adapter, seven-slot budget and original deterministic verifiers remain the execution path; no replacement executor or LIVE/account resolver is installed.

`extract_pb` binds the exact source Run/Attempts and actual NS plus controller REQUEST/RESPONSE/SENT archive chains, original extraction key, Recipe, different complete Goal/material, account, principal/project, approval and budgets. It invokes the original extraction write group on the same transaction, with fresh source/authority/account/expiry checks afterward. Existing generic extraction API remains generic, without an HTTP fee/authority override or automatic trial selector. Initial extraction rollback/refusal cases passed only on the earlier `55c45e1e656782ec6dc4579e9c9fd1abedcb6a6e` source revision; they do not qualify the final candidate.

The later bounded source-proof candidate reuses a fully validated source binding/proof only inside the synchronous readonly `bound` or controller `_pb_source` call. It binds exact Store/connection/SQLAlchemy transaction/real SQLite driver transaction/write epoch/thread/user/project/source/full Limits. Every hit rechecks all captured logical authorities and the current token/Limits; values are deep copies, incomplete recursive proof is refused, and writes (including failed writes), transaction exit and exceptions invalidate it. No approval, account, budget, permit, source-audit-only hash or Worker lease is cached. Complete original `source` and `bound` bodies are AST-equal after private extraction. This mechanism has static review only; its fourteen runtime counterexamples have NOT RUN.

The normal test now uses the original extraction-by-key GET for lost-return recovery, and the lost Cold test includes a fresh Store/Worker no-send check. Neither new assertion was reached on the final candidate; they are not runtime evidence.

Product candidate `3ec30da9a36b0ef0ae1a844bd43622d5630b0d5d`; qualified source/test HEAD `e26f9a83b35f5979b89a65296d642a44f8c969e6`; pin `b1b6f128efdf1d75195a42c8867afa393112382aa8dd7c2f5a01210a2bcf29dd`. The exact 86-module inventory, original anchors, CHANGED set and normalization are unchanged. No Run deadline, 30-second lease, >=60-second request gap, quota, approval or unknown-result settlement restriction was extended. The P-B fixture creates its new synthetic approval with TTL1800 at initial approval creation; no existing approval or Run timestamp is rewritten or extended during execution.

## Actual terminal validation

| Batch | Source | Result | RC | Wall time |
|---|---|---|---|---|
| initial-pb | 55c45e1e | 9 PASS / 6 FAIL / 0 ERROR / 0 SKIP / 0 INTERRUPTED | 1 | 895.059s |
| pa-shared-regression | 55c45e1e | 29 PASS / 0 FAIL / 0 ERROR / 0 SKIP / 0 INTERRUPTED | 0 | 529.392s |
| legacy-admission-extraction | 55c45e1e | 45 PASS / 0 FAIL / 0 ERROR / 0 SKIP / 0 INTERRUPTED | 0 | 325.494s |
| actual-error-normal | 55c45e1e | 0 PASS / 1 FAIL / 0 ERROR / 0 SKIP / 0 INTERRUPTED | 1 | 400.134s |
| segment-v1-pb | e26f9a83 | 0 PASS / 0 FAIL / 29 ERROR / 0 SKIP / 0 INTERRUPTED | 1 | 234.431s |
| segment-v1-recovered-pb | e26f9a83 | 0 PASS / 0 FAIL / 29 ERROR / 0 SKIP / 0 INTERRUPTED | 1 | 132.584s |
| segment-v1-admission-regression | e26f9a83 | 51 PASS / 0 FAIL / 0 ERROR / 0 SKIP / 0 INTERRUPTED | 0 | 242.478s |

Results are per frozen source revision and must not be combined into a final-candidate acceptance total. Every batch preserves COMMAND, process exit, raw stdout/stderr, XML/hash, exact 502 src/tests/pyproject before/after/copied-file closure and clean unchanged HEAD. Known restricted SQL/UDF/barrier modules had **zero import attempts and zero loaded modules** in every batch. No restricted tests or alternative private diagnostics were run.

`initial-pb`: 9 extraction refusal/rollback cases passed; normal Cold failed and five Cold fault tests failed before their `injected == [fault]` assertion could succeed. These failures are not successful negative coverage. `actual-error-normal` then reproduced `RESOURCE_UNAVAILABLE: Heartbeat renewal could not acquire the database lock`, with a preserved normal caught-error traceback to background heartbeat `BEGIN IMMEDIATE` / sqlite3 `database is locked`. That identifies the operation, without quantifying source proof CPU time or lock-hold causation. Its first capture accidentally serialized the public method as text; original bytes remain, and the later capture calls `error.public()`.

`segment-v1-pb`: all 29 named XML cases are ERROR from one module-prefix source assertion (RUNNING instead of SUCCEEDED). Its caught source reserve/preflight failure is the composite identity/cancellation/version/finite-lease guard; no single predicate is inferred. `segment-v1-recovered-pb`: all 29 ERROR again share one prefix failure, this time Generate returned FAILED with public `VERSION_CONFLICT: Stale worker lease` instead of PARTIAL. The 29 test bodies are NOT RUN in each batch, not 58 independent product defects or skips. Cold and all fourteen memo counterexamples remain unexecuted. Prefix retries stopped after this one unchanged-source confirmation.

The first segment batch also lost the exec-server transport connection. Recovery found a complete durable PROCESS_EXIT/RESULT/XML already written; this is separately preserved as a tool transport error, not an authorization denial or established cause of the pytest failure. V1/V2 scalar-metadata query setup mistakes and V3 symlink duplicates are retained and explicitly corrected in V4; no private bodies, SQL hooks, UDF or profiling were used. Earlier P-A29/legacy45 results remain tied to their earlier source and cannot replace current P-B validation.

Full-source Ruff PASS. Mypy RC1: the same five existing errors in `status_report.py`/`tools.py`, 87 source files; zero new errors. Not a green type-check or remote CI claim. Independent reviews preserve the pre-test decorator placement finding/fix, exact original body AST checks, frozen static review and red-batch classifications. Static approval does not establish runtime correctness.

## Concrete blocker and retained gates

The original finite Generate/Source prefix currently cannot reliably reach a successful source under its unchanged guards. Therefore this candidate has no completed P-B normal/fault acceptance and no demonstrated minimal fix for the initial Cold heartbeat-lock failure. No repeated prefix retry, new performance probe, old peer-version diagnosis, deadline/lease relaxation, unknown resend or forced pass was used. The independent candidate branch is retained for review, not promoted/merged.

Fixtures and any cloned successful prefix are isolated synthetic SQLite data; they do not demonstrate shared quota coordination across separate databases. Real model/paid API calls: **0**. LIVE remains closed. Real account/free-entitlement/nonchargeability, PostgreSQL, Windows, native browser, human semantics/owner acceptance, deployment, remote CI, complete live P-A/P-B and old-database upgrade are **NOT RUN**. Original full389 **388PASS/1FAIL/RC1 remains NOT_ACCEPTED** and peer_version remains unfixed. Protected main/core and all earlier development refs and unrelated WIP are checked separately after ordinary push.

Evidence: [manifest](../evidence/pb-production-wiring-20261015/MANIFEST.json), [archive receipt](../evidence/pb-production-wiring-20261015/ARCHIVE.json), and `pb-wiring-evidence.tar.gz` in the same directory. All initial failures, later setup errors, exact commands/source closures, synthetic fixtures, tool-error recovery, and independent reviews are preserved. Post-push full-SHA/remote/clean-tree verification is a separate receipt; no CI success is implied.
