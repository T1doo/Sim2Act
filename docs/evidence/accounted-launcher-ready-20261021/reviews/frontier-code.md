# Launcher candidate profile — initial frozen code review

2026-10-21. Independent read-only review. Result: **P2_METADATA_NONINTERFERENCE_FIX_REQUIRED**. This is an initial exact-hash review, not final code/launch ACK. Reviewer executed no product/import/test/database/Worker/Mock/G0/prefix; no grant or run directory was created and no repository files were edited.

## Exact reviewed files

All seven current SHA256 values were independently computed and match `/tmp/sim2act-launcher-profile-ready-20261021/frozen-hashes.json`:

| File | SHA256 |
|---|---|
| `src/sim2act/_cold_accounted_native.py` | `7f8a3fd26ef56da5d344504a6629a72d0f85b30221571d8ed05f77e876ed3e45` |
| `src/sim2act/cold_accounted.py` | `dd62f77a779f8715acc380298c1c76d1076cd61cc58f16e1c2b73822ed2361a1` |
| `scripts/diagnostics/g0_bounded.py` | `131956a6b89f8c7dffe546aad5ed1fc0e8a9617b87a7ac2e93326270a5bb8be6` |
| `scripts/diagnostics/g0_prefix.py` | `5df94e40773b8b8c42137494b21ca7c441c3fb00c7582e33ed709539a4e4ecec` |
| `scripts/diagnostics/test_g0_guard.py` | `dc9c1634a5c71ead3e1ea48e1fd4f8c34e5e3441bb1cb22cf942d2b4f355bb1d` |
| `tests/test_cold_accounted_mock_wiring.py` | `f29cf24ea5bed295f78bdd7c862d3555f616ce22a0b85f0c602403eb7c0fdbf9` |
| `tests/test_cold_accounted_launcher_ready.py` | `f3411000a2488920de0c34967f163b00c4634b8b42c5a3f3d8f3f88b42837729` |

## P2: observation can change routing, mask errors and skip cleanup

`_NativeCandidate.choose` adds `selection = dict(... budget=self.budget_record(ledger))` at the start of its original exception path, before `mode.close()` and `ledger.close()`. If this diagnostic construction raises, the original exception is replaced and both cleanup calls are skipped. This is particularly visible with a pure diagnostic `budget_record` failure such as RuntimeError; no product execution is needed to establish the control-flow defect.

`_OwnedPrewriteMode._select_completed` likewise calls `native.budget_record(budget)` in the Capacity catch before the original `packets.clear()`, budget close and LEGACY return. A diagnostic-only exception there changes an originally valid conservative LEGACY selection into an error; the outer choose diagnostic can then fail again before cleanup. These records are intended to be non-authoritative and cannot be allowed to change that route.

The prefix observation also performs unprotected record construction and field access in `CandidateObservation.wrap_commit` after original success and while handling original exceptions. A recording exception can prevent the original return or replace the original error. Its later report construction can replace error evidence before the original exception is re-raised. Keep recording failure separate from business behavior.

Minimal correction: isolate observation updates behind narrow Exception handling and a bounded incomplete flag, retain original success/return/exception and existing cleanup/fallback order, and make cleanup independent of recording success. A diagnostic failure must produce incomplete/UNKNOWN reporting rather than a new permit, fabricated metadata or a changed route. Do not catch business validation with the metadata handler. Add local observer-fault cases that preserve original LEGACY, original error identity and closed scopes; they do not need a prefix or G0.

## Other reviewed paths

The launcher mode/profile design is implemented as one frozen candidate profile with two-family classifier aggregate, computed exact work, named logical limits and explicit non-CPU/RSS claim. Canonical JSON comparisons distinguish bool/numeric type substitutions and reject nonfinite data. Candidate scope/profile digest participates in exact grant matching, and execute passes its explicit flag to describe. Child constructs only the expected profile from consumed description; CLI child cannot select candidate independently. Default description has no candidate fields and returns config None. No account-evidence or production qualification is supplied.

Required audit/authorizer/owned-process API checks are included in description and rechecked by child. Child I/O installation precedes candidate config/product-prefix import. The additional guard tests are same-interpreter protection units, with no product imports in those child snippets. Optional native VFS support is explicitly unnecessary for this sampled-disk branch; none of this establishes a filesystem hard quota.

Target-local observation wraps original commit, records entry/return separately, copies only successful original authority deadline tuples, and sets scope_returned only after original context fully returns. Parent candidate completion requires exact route, two returned commits, valid final finite deadlines equal to the second return record, original scope return and logical ledger zero/closed. LEGACY completion is separately named and does not qualify OWNED. UNKNOWN is rejected by parent. Identity/ordering/completion intent is appropriate, subject to the observation-failure isolation above.

## Verification limits

New local test source exercises profile exact matching, missing API refusal, describe-only CLI, local OWNED/LEGACY metadata, two commit/scope markers and original context-exit failure. It uses local SQLite/helper contexts or stand-ins; no actual prefix/G0. The author reports guard units and an in-progress broader pytest batch. No final test result is attested by this static report, and no execution permission follows from it.
