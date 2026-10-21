# Launcher candidate profile — final closure review

2026-10-21. Independent read-only review. Result: **LIMITED_IMPLEMENTATION_AND_LOCAL_EVIDENCE_ACK_NO_GRANT_NO_WINDOW**. The initial metadata noninterference P2 is closed for ordinary observation Exceptions in the final implementation. No new P1/P2 identified in the reviewed increment. The earlier LAUNCHER-CODE-REVIEW remains an initial seven-hash finding record, not an ACK of these final bytes.

## Final exact files

These current SHA256 values were independently computed and equal `/tmp/sim2act-launcher-profile-ready-20261021/final-hashes.json`:

| File | SHA256 |
|---|---|
| `src/sim2act/_cold_accounted_native.py` | `85e493b32ce1bd80824652e08e93ab484c6e6137999b0ec622db0083823aea76` |
| `src/sim2act/cold_accounted.py` | `c8afddb4aedb0b651e2797aa9d9c59356abd2b169a27e7cf749bf8fbde02b427` |
| `scripts/diagnostics/g0_bounded.py` | `15999ea969ebc6729d96852108bef956649592d92dc4c9a9decf089006889760` |
| `scripts/diagnostics/g0_prefix.py` | `b42a5e104ee595f1633414a84a8e90c44788e1b6f06a45c5eb8f8df28680d5c9` |
| `scripts/diagnostics/test_g0_guard.py` | `dc9c1634a5c71ead3e1ea48e1fd4f8c34e5e3441bb1cb22cf942d2b4f355bb1d` |
| `tests/test_cold_accounted_mock_wiring.py` | `f29cf24ea5bed295f78bdd7c862d3555f616ce22a0b85f0c602403eb7c0fdbf9` |
| `tests/test_cold_accounted_launcher_ready.py` | `97bd58d348c8f1e4a27e170192e1d72338f1275af6f7d7f739db478bcff0deb0` |

## P2 closure

Native phase/route/budget updates now pass through `observe()`, which catches ordinary observation Exceptions and marks diagnostic_incomplete. The Capacity handler therefore continues original full-current check, packets clear, ledger close and LEGACY return even when budget-record construction fails. `selection_record()` provides an incomplete UNKNOWN record on its own observation failure. These records remain outside graph inputs and permission checks.

In `choose`, error observation is enclosed by finally cleanup, with mode close and ledger close in nested finally blocks. A normal budget-record failure can no longer replace the original business exception or skip cleanup. This does not claim that arbitrary BaseException, failed cleanup or process exhaustion is recoverable; existing failure/UNKNOWN protections remain required.

Prefix commit recording separates metadata failures from the original call. Original commit executes and its return is preserved even if output-read recording fails; original exceptions are re-raised unchanged after best-effort error recording. Report construction failure returns an incomplete record rather than replacing the original error/reporting path. Missing/invalid observation cannot establish completion. Original context scope_returned is set only after its complete return; candidate report combines trace validity, two original commit returns, available finite deadlines and original scope completion. Parent now explicitly requires top-level `diagnostic_incomplete is False`, in addition to route/commit/deadline/released-ledger checks.

Local regression source directly injects RuntimeError from budget_record on OWNED and forced LEGACY, checks unchanged route and closed zero-live/resident ledger, injects an original DomainError plus broken metadata and checks exception identity/cleanup, and exercises commit output-read / append recording failures without replacing the original return/error. These are local helper/stand-in cases, not production-prefix execution.

## Retained launcher and qualification boundaries

Fixed profile/mode and canonical exact matching remain as reviewed: candidate flag binds a distinct description scope, profile and profile digest; parent validates a matching newly supplied grant before consuming/creating an execution root; child reconstructs only the frozen known profile from the consumed description, with required protection checks and installation preceding prefix work. Default selection remains None. No arbitrary numeric profile, public/environment/Worker configuration, account evidence or production qualification is added.

The two-family fourth-power classifier ceiling and additional equal fuel are explicit logical limits, not a guarantee of OWNED over the whole Bounds domain or total CPU/RSS bounds. Sampled disk remains explicitly sampled rather than a filesystem hard quota. Completed LEGACY is separately labelled; selected errors/incomplete records stay UNKNOWN and fail candidate completion. This review does not change original account gates, configured test substitutions, deadlines, Mock budgets or cleanup budgets.

## Author originals read, no reviewer execution

Read original `/tmp/sim2act-launcher-profile-ready-20261021/closure-junit.xml`: 131 tests, 0 failures/errors/skips, 95.991 seconds; closure pytest log reports 131 passed, one warning, 95.99 seconds. Guard log reports 33 units in 0.157 seconds, OK with 4 optional VFS skips (29 passing), not 33 passing. Mypy log reports success for 2 source files. Initial closure Ruff output records I001 import ordering in the new test; final Ruff log reports All checks passed. The author states the intervening fix only reordered imports in the final test file; this is not described as a second 131-case run on the final import bytes. Current final seven hashes were independently read; test execution was performed by the author, not reviewer.

Evidence SHA256: closure JUnit `41fbf1f57da9bb55a2a797cf94684d1f091c499a053cf0db92fc4d8c67b319b3`; pytest log `f03bcacb762cd7ef3fc796b70e30161b29e971455c829d28efd763ffa6e881ab`; guard log `c28a4204b596a70f9fbb7a81670da7c615a6c08f99f3f3880274316627d12590`; mypy log `f9b031e5c45aa702cd4fef028d465551cb20a2c4698e0913c7b00766b20ac4d8`; initial Ruff `bfbba3db866e46d58c7e4a977a6fc5fdde62baa49cd49017a54f716b85e6dacf`; final Ruff `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`.

Reviewer performed only source/diff/hash/log reads and /tmp report writes: no code or product imports, tests, database access, Worker, Mock, G0, prefix, prepare/commit or launcher execution. No grant or execution directory was created. This implementation/local-evidence ACK requires no new grant and does not permit an execution window. Full actual G0 candidate behavior, performance/deadline success and production/account reachability remain unverified.
