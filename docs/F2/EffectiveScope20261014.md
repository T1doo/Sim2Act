# PB effective-limit same-segment correction

Previous delivery: `2797f75a641b52ddccfd84f98505b7a0e4d8ba28`. [Existing v6 PB P/F/P ordinary stage projection](ExistingV6PBStages20261014.md) retains both success and the real BUDGET_EXHAUSTED failure. The failed run did not collect detailed timings; transaction waits and per-phase fence attribution remain NOT RECORDED. No new probe/database read is used to fill that gap. Nested durations overlap.

Core `30c7ada5035c37e5e93af00fb4b3bead9f589a4d`; qualified source `efeebb147665c2fc492bdd77629ab9a7988db96f`. Effective limits previously entered frozen_contract/source_scope_gate again directly after a complete bound/guard in the same read-only call segment. Archived successful paths observe two effective calls at 2.33–4.05s each. This is a specific repeated-work contributor; it does not close the unmeasured failed-run root cause.

Only the two existing internal effective callers use `_scope_checked=True`: reservation_check after full bound/receipts/intent, and advance_model immediately after commit_guard. Default callers still run frozen_contract. The selected helper always performs the original complete typed/hash/resource/Goal checks; worker, manifest, frozen contract and action limits retain every field's minimum and original list evaluation order. No proof is reused across transactions, writes or callbacks. All post-write and post-response gates and original budgets are unchanged.

Independent actual-source static review confirms runtime AST is identical to the previous delivery after reversing these three edits, Store helper bytes unchanged, 77-file qualification map/pin exact and original baseline/anchor rules unchanged. It ran no Worker/tests/private diagnostics. All 11 actual suite labels completed on this qualified source with **65 PASS / 0 FAIL / 0 SKIP**, 62 unique test identities. The three repeated executions are two additional PB correction attempts and one repeated PA page, not additional unique coverage. Every suite's 465-file before/after closure is exact; no source mutation occurred during any Worker run. All business commands terminated before packaging.

| Actual suite | Executions / PASS | pytest wall seconds |
| --- | ---: | ---: |
| qualification / lease / foundation | 50 | 11.824 |
| fresh modified PB parent | 1 | 491.434 |
| fresh modified PA parent | 1 | 284.056 |
| exact PB correction | 1 | 277.533 |
| exact PB repeat | 1 | 290.742 |
| PA correction | 1 | 132.939 |
| six late callback faults | 6 | 186.492 |
| PA current HTTP / offline page | 1 | 144.832 |
| PB original-key lost-response page | 1 | 318.864 |
| deliberately concurrent PB correction | 1 | 292.725 |
| concurrent PA page | 1 | 167.304 |

The two deliberately concurrent cases use separate independently copied fresh-source databases and unchanged budgets. They constitute a limited two-case workload, not exact reproduction of every load during the old failure. All three PB corrections have public SUCCEEDED/result_version2/PENDING/semantic UNKNOWN receipts; exact fence and accepted-to-commit duration are not in these public receipts and remain NOT RECORDED. Whole pytest times include preview/control/final-review operations and are not single Run lifetime measurements.

Three PB ordinary timing histories (2,017/2,097/2,099 records, all below the 10,000 cap) each record one Store.claim and six returned advance_model calls, without an advance_model error. No effective call met the existing >=0.1s recording threshold. This contrasts with the existing v6 observations of 2.33–4.05s effective calls and two recorded claims, supporting removal of that specific duplicate entry. It does not measure zero effective cost or exact transaction waits. Each new PB case still records one ~5.01–5.07s heartbeat OperationalError; no claim that all lease/locking trouble disappeared is made. Nested timings overlap and must not be summed.

PA/PB page checks are **32 + 34** with 20 current HTTP assets matched per flow; the deliberately concurrent PA repeat adds 32 observed checks but no new page coverage. PB lost-acceptance response resumes only by the original key GET and has one correction POST. New results stay PENDING and receive a fresh simulated independent review; no real semantic acceptance is inferred. Normal corrections preserve old histories, Goal/draft/release objects, exact duplicate semantics and grandchild refusal.

Late mock callbacks fire exactly once in each case and make one synthetic request: target/check permission revoke WAITING_RESOURCE (2), source/competing version and withdrawal FAILED (3), cancel CANCELLED (1). All have no child typed/save. Passing these expected rejection tests does not make WAITING_RESOURCE a successful execution.

Ruff passes. Mypy reports the same five baseline errors in status_report.py/tools.py, no new error. The old v6 P/F/P and v4/v5 failures remain sealed in the prior delivery; none is erased or relabeled. These new finite normal and limited concurrent regressions pass, while the old failed run's unrecorded full stage/transaction-wait root cause is not claimed closed. All new commands/raw histories/source maps and independent reviews are retained.

Private UDF diagnostic stays BLOCKED without retry/rephrasing/reconstruction/replacement. PG, Windows, native browser, real/paid models, true human semantic acceptance, full P-A/P-B product acceptance, remote CI and deployment are NOT RUN.

## Sealed evidence

[Full current evidence archive](../evidence/logic-correction-effective-20261014/logic-correction-effective-evidence-20261014.tar.gz), SHA256 `35d3232d59e71c80dc134af8bcfd785c2efa3056b624f22a96ae86ad176c44bc`: 1,963 members read back and hash-verified, 12,823,200 compressed bytes. [Archive receipt](../evidence/logic-correction-effective-20261014/archive.json). The prior [2797f75 delivery](LogicCorrectionStage20261014.md) and its full failed histories/archive remain unchanged.

Actual-source review FINAL SHA256 `982b9e5a471b09a8e8e28d3946babd6f4d953d207b925ccc0dcedd77a4a846ff`; final public-evidence review FINAL SHA256 `b8ad60d0a3c0eb6f6620f2cb4bb94048461fff41c453b0976b0693bd3b2b8513`, MANIFEST SHA256 `604fee958e29c92790dd0b39dfbbe90c8b50cba4c8a1206b93aa2f962f31b016`. Reports are sealed in the archive; reviewer dynamic test/Worker count is zero, fully overlapping author evidence rather than extra coverage. Normal development-branch push does not imply CI green or release acceptance.
