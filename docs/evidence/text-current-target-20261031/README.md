# Current exact software qualification restores the existing text continuation flow

Frozen application: `7e29ffb397d7d7560ebdf617aa345830bc34ee33`, parent `4508a8e36f67a9e1870cadabb38a885b0261e96d`, development branch only. Prior cancellation and finite-commit fixes remain. No application source, browser UI, C/h source or native binary was removed to obtain qualification.

## What the 58 failures actually meant

The retained earlier full XML under [cancellation recovery](../cold-cancel-recovery-20261031/README.md) has 58 failures. Sixteen first failed in the test's `rows()` oracle: it queried today's metadata against exact historical databases that did not contain later tables such as csv_owner_records. The other42 failed before their intended mutations: preflight expected201 but current complete software was rejected409 by the old reviewed-target manifest. They were not58 demonstrated application regressions, and the latter42 had not executed their negative cases. The two earlier baseline4c controls were representatives of the shared entry failures, not58 individually rerun baseline tests.

| Old entry failure | Tests | Exact old cases |
| --- | ---: | --- |
| Current metadata invents old-DB tables | 16 | Normal cold continuation2; full-history proof mutations10; genuine failed-history2; corrupted failed-queue2 |
| Complete target unqualified | 42 | Commit-CAS mutations18; other-instance, atomic-insertion, preflight cancellation, private-preflight revocation, absent marker, late revocation, final-response recheck, cold-private-read, late cancellation, original-key recovery, metadata stop and terminal-history mutation:2 each |

First, the oracle now reflects every actual historical table and column, including unknown ones. Running that alone exposed the next real setup prerequisite: current API also requires later csv_report_workflows tables. `text-continuation-reflected-before-*` retains that original failure. The supported startup uses explicit structural preparation before starting API/Worker; the fixture now invokes the existing Store.initialize **only on its copied synthetic database**, never implicitly in the API. It verifies every original row and complete sqlite_master DDL row (type/name/tbl_name/sql) remains, all added tables are empty/current-metadata tables and new schema objects are only their table/index objects. It does not rewrite old seals or old approval TTLs, or pretend to repair unknown missing columns. Exact source .db.gz fixtures/info and historical software anchors stay unchanged. The next retained `migrated-before-*` still fails the real qualification gate409; migration did not grant execution.

## Actual product repair

Current software had146 Python files versus86 in the last text-target manifest, with60 additions and39 changed existing files. The complete new target is reviewed and pinned; the original CHANGED name set, historical anchor hash, accepted historical source set, ownership, grants, approval consent, revocation, CAS, limits, private-read ordering and history checks remain. Success assertions stay201/202 and all original negative cases actually execute. No fixture stubs known()/qualified_target()/implementation() into accepting software.

Production and historical text qualification each had a manifest pin inside the other's complete source set. Updating only one would break the other; blindly repinning both creates a digest cycle. Production qualification v2 normalizes exactly two unique, top-level, simply spelled64-hex assignment literals: its own production pin and text_continuations' text pin. All157 production py/C/h/catalog entries remain exact; config.py is only the original existing exception. Its strict duplicate-rejecting independent text-manifest check derives the expected146 Python hashes from the **same captured source bytes that passed production proof**, normalizing only text's own pin and preserving the actual production pin. It never delegates the decision to a replaceable continuation callback. Both historical and production gates reject changed/unlisted content; no filename or callback exemption was added. Historical anchors are read once for both SHA and strict parsing.

The text manifest retains its v1 normalization rule and exact accepted historical sources. review_baseline identifies the prior reviewed text-target input9ecdb803; review_candidate identifies the supplied4508a8e3 input before this repair. The final reviewed repair bytes are the manifest's complete exact hashes and the frozen7e29ffb3 commit above, not a claim that4508 already contained the new closed-proof code. The offline generation script is archived for reproducibility and has no runtime invocation.

Production manifest SHA256: `583295f4d86f60b25bdee53d21bf85ff3f2699519f76c1cc15c971e4e0eea82f`.
Text manifest SHA256: `3ef01e3ec5b89390fd56a5412136f5f6964dab6b4541246f1e94aeb1c1c5d03b`.

## Actual validation

First repaired continuation+target run:80 PASS (58 original continuation cases +22 exact-target cases). First pair-closure run:25 PASS. Independent review then required single-read anchor hashing/parsing; this was fixed and its read-once negative test added. Duplicate-production-field synthetic resealing counterexamples were also added.

Final actual command, no test stubs or skips:

```sh
.venv/bin/python -m pytest tests/test_text_continuations.py tests/test_text_software_qualification.py tests/test_qualification_pair.py tests/test_natural_cancel_recovery.py tests/test_sqlite_commit_boundary.py tests/test_model_settlement_interval.py tests/test_production_trial_admission.py -q --junitxml=/workspace/scratch/continuation-lifecycle-final-20261031.xml
```

**207 PASS / 0 failure / 0 error / 0 skip**,211.672s, started2026-10-31 16:08:59UTC, completed16:12:31UTC, process exit0. Breakdown:58 continuation,22 historical-target,27 dual-proof counterexamples,25 cancellation recovery,19 commit-boundary,13 interval,43 production-admission tests. These are targeted suites, not a whole-repository-green claim.

The58 preserve original known-source/instance boundaries, full historic success/failed rows, old typed version1, explicit continuation/revision2, new cold Worker typed version2, actual citations, original-key recovery, and permission/late-mutation/expiry/atomic-failure negative assertions. The cancellation/commit suites separately preserve terminal CANCELLED, repeat-cancel idempotence, fresh-process no replay, live-owner refusal, full rollback and finite-deadline-before-commit rejection. Synthetic virtual TTL used by old historical fixtures is **not performance evidence**.

Final independent readonly review checked code,157/146-entry closures, both literal pins, original anchors/CHANGED and207-case XML; no remaining must-fix. This is review of qualification/continuation-related behavior and closure, **not a full security audit of146 modules**. Reviewers neither wrote source nor reran the tests.

## Live transport, startup and remaining boundaries

Separately, before this repair, the existing fixed free Intern route completed [two real requests through the basic F1 API/Worker/resource.read/persist/reopen path](../intern-basic-worker-live-20261031/README.md), using1,526 tokens without retries. That actual source is4508a8e3; relevant F1 component files remain unchanged in this repair. Its Run is truthfully PARTIAL/goal_acceptance NOT_RUN. It is not a full live Source/Cold semantic acceptance, and the synthetic desktop still deliberately disables model dispatch. Formal PG/approved trial input is not invented to bypass that boundary.

The independent EXE/WebView2 startup source and compact UI are unchanged. This repair adds no runtime file or native extension and requires no new runtime install; four existing backend .py/.json files changed and must be included as one exact frozen source/package input. No new Windows build/UI execution was performed here. Do not mix this backend with an old package identity or mark it target-machine-tested.

Previous two-large-Cold save/reopen/cancel evidence remains bound tobbe2a11c/4508, G0 29.41/31.34s, writer scope44.29/45.97s. This repair did not rerun or establish a speedup for that large fixture; stable30 seconds and long-writer performance remain open. Neither original lease/admission nor signed120-second settlement caps were enlarged. Formal PG/live-Close and current Windows qualification are separate from the now-passing continuation workflow. No PC, new Windows CI, main/Release, paid service, new production credential, role, permission or deployment was used.
