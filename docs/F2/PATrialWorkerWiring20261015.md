# P-A trial wiring through the existing Worker — 2026-10-15

The former actual seven-slot fixture patched the transport class to add trial accounting; the default production admission used a canned sender only. This slice adds a server-owned `PATrialBinding` to the existing Worker and captured InternModel adapter. It executes only explicit isolated SQLite/MockTransport fixtures. Production account/free-entitlement/enforced-nonchargeability resolution remains absent and LIVE remains closed.

## Implementation and contracts

`pa_trial_dispatch.py` binds the original approved Generate3/Source2/Cold2 contract, exact canonical account quota, approval, owner/project, stage authority, software qualification and budgets. Original Worker reservation appends the slot and actual request archive atomically with Attempt/reservation/context/event. Original adapter guard is followed by fresh admission and one durable send marker before IO. Captured original decoded response/prefix is recorded before original business validation; verified settlement joins complete request/response/event/wire/marker evidence inside the existing checker/candidate/NS verification transactions. Current auth/cancel/version/lease/fence checks remain active, with no new executor and no lease or deadline extension.

The public budget methods retain their original interfaces. Independent AST comparison proves the extracted transaction bodies are unchanged after the helper docstring/transaction precondition. No HTTP fee/account/callback override, credentials, real model request, deployment or protected branch change.

A DB marker cannot atomically fence external HTTP. A late received body may become an owned fact while business acceptance is refused. Explicit response archive failure means NOT_PERSISTED, nonrefundable UNKNOWN and no automatic archive retry. The existing first generation resource.read receipt was committed earlier and is not claimed to roll back. Completed history cannot gain new archives; original-key recovery reads without resending/refunding/re-enabling.

## Actual validation

| Batch | Terminal result | Wall time |
|---|---|---|
| initial-faults | 19 PASS / 1 FAIL / 0 ERROR / 0 SKIP; RC1 | 34.036s |
| revised-pa | 29 PASS / 0 FAIL / 0 ERROR / 0 SKIP; RC0 | 516.748s |
| budget-production-regression | 79 PASS / 0 FAIL / 0 ERROR / 0 SKIP; RC0 | 606.140s |
| existing-worker-regression | 13 PASS / 1 INTERRUPTED / 8 NOT RUN (corrected; RC2) | 362.371s |
| allowed-rollback-remainder | 5 PASS / 0 FAIL / 0 ERROR / 0 SKIP; RC0 | 132.660s |
| strengthened-injections | 9 PASS / 0 FAIL / 0 ERROR / 0 SKIP; RC0 | 20.606s |

The seven-slot run made **7 actual OFFLINE MockTransport sends**, retained **14 request/response archives**, recorded synthetic KNOWN **7000 tokens** / reserved envelope **48354**, and preserved the transport class. Six real gaps in seconds: 60.427748, 60.768734, 70.294362, 70.311219, 74.151490, 81.726146. Freshness refresh is explicitly synthetic fixture data, never real account or fee evidence. All seven slots accepted only after original deterministic checks; citation validity is not human semantic acceptance.

The first 19PASS/1FAIL was a test-injected process-loss RuntimeError escaping before UNKNOWN assertions, not an erased history. The revised test catches only that exact injected exception and proves the durable unresolved slot/marker and no success. The final assertion batch additionally proves all eight pre-send injections executed and verifies original-key recovery from a new Store/Worker after lost response, with no additional adapter send. The seven-slot test function AST and all product source remain unchanged by that assertion strengthening.

Source qualification: candidate `e02e84632331d6f4aafb6fe92d6a13210b2fe5b3`, pin `449cf2b6018b3d8e62b32aab511e323cc89f458c0bb4caa73b7bd2ee71117bb6`, 86 exact qualified modules. Seven-slot/initial regression source SHA `95d0d501c14d8536968655b3cf168564c54cb4b8`; strengthened assertion SHA `f8c3dad5c4c3dba9e7e3e73510f775cdee8fe501`. Every batch captured and read back 501 src/tests/pyproject files with unchanged before/after/copied bytes, HEAD and clean tree. The strengthened batch is a separate frozen test revision; no claim that all cases ran in one final-SHA full suite.

Full-source Ruff PASS. Mypy: 5 existing errors in status_report.py/tools.py, 87 source files; zero new errors. Not a green type-check or remote CI claim.

## Independent review and retained interruption

Reports preserve the initial implementation findings, the pre-send P2 fix, budget AST proof and final evidence review. The legacy runner mistakenly selected `test_natural_spec_callback_reads.py`, which imports the known restricted private SQL/UDF barrier module. Root stopped its own pytest with SIGINT before the four callback test bodies; collection import did occur. No alternate barrier/UDF tool or diagnostic was attempted. Stdout confirms 13 completed PASS; XML adds one unnamed interrupted artifact which the original naive RESULT counted as PASS14. Original XML/RESULT are preserved; INTERRUPTION_CORRECTION.json and the independent review establish **13PASS/1INTERRUPTED/8NOTRUN, RC2**. Five independent permitted rollback cases then ran separately; the four restricted callback cases remain NOT RUN. No barrier/UDF evidence is claimed.

## Remaining gates

Original complete389 **388PASS/1FAIL/RC1 remains NOT_ACCEPTED**, including the un-erased peer_version failure; no new peer diagnostic or blind complete389. P-B production wiring is not part of this slice. Real provider/account/free entitlement/enforced zero charge, LIVE, PostgreSQL, Windows, native browser, human semantics, deployment, remote CI and full live P-A/P-B acceptance are **NOT RUN**. Overall release remains closed.

Evidence: ../evidence/pa-production-wiring-20261015/pa-wiring-evidence.tar.gz, MANIFEST.json and ARCHIVE.json. These contain immutable failures, exact commands/process exits/XML/source closures, raw fixture outcomes, reviews and corrections. Final ordinary branch push is verified separately by exact remote SHA, 13 protected refs, clean 0/0 state and unchanged unrelated WIP.
