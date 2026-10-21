# Receipt continuation: frozen test evidence ACK

**ACK for the author's final frozen local regression evidence.** The six current file hashes independently match `frozen-before.json` and the final source ACK. No new blocking discrepancy was found in the reviewed logs, JUnit, lint/type results or hash bindings. This supplements the frozen source review; it does not execute or authorize a window or prove G0/deadline/performance acceptance.

The reviewer only read original test artifacts and source hashes. No tests, DB connection/query, product, Mock, model, G0, profile or signals were executed and no repository file or grant was written.

`/tmp/sim2act-receipt-closure-20261021/tests/frozen-final.log` records **109 passed**, one existing Starlette deprecation warning, 195.61 seconds. JUnit records 109 tests, zero failures/errors/skips, 195.607 seconds. Independently counting its testcase elements also gives 109: 22 receipt tests, 27 native tests, 24 composite-stage-pin tests and 36 accounted SQLite tests. Ruff reports all checks passed; mypy reports no issues in four source files. These are author-run local, synthetic SQLite/helper regressions, not a new Worker/Mock/native full prepare/two-commit/G0 run. They retain the earlier source ACK's default-off, early-SELECT, logical-budget and baseline-exclusion limitations.

Historical failures remain separate: `targeted.log` records **68 passed / 1 failed**, 106.46 seconds; `receipt-final-initial.log` records **21 passed / 1 failed**, 42.90 seconds. The former reached the existing software-change guard while source was being edited, according to the author; no independent intermediate-byte reconstruction is claimed. The latter used the enormous generic fixture allowance for a test expecting finite-capacity fallback. Its explicitly finite allowance correction is a separate **1 passed / 1.72s** record. None of those earlier logs is relabeled all-pass. The final 109-test run is the distinct complete passing artifact.

| Frozen file | SHA-256 |
| --- | --- |
| src/sim2act/_cold_accounted_native.py | b6ab0b09f6abb9d8ddcd72b54127af0517a1d0f67728d96582c90e0f4d2c7147 |
| src/sim2act/_cold_accounted_receipts.py | 49f0c0ff3cb6583d02cee96f7125fe237f5fb4c2d52ea8b1e39d282f42e2fca2 |
| src/sim2act/natural_spec_runtime.py | eeab5367c95502f0ba57f194519f46a3cbe054ef0150051ba3c3126b9182ea57 |
| src/sim2act/pa_spec_apps.py | 6197df6c98bf1eeff463c7fc7b99c9c48e9fe308969fde8243715091a31712d6 |
| tests/test_cold_accounted_native.py | 8cd4a58481e9e11c718bbf1e0c031f7946112f81d9a33e100fcdf3d5ee6017a4 |
| tests/test_cold_accounted_receipts.py | a7550caa54528afd656f77e724121a7c5e9e40537e13d87b376c9d7b0623beb9 |

| Original test artifact | SHA-256 |
| --- | --- |
| frozen-before.json | ffac0048b895e7b8c013d969ad3c4d6b44f4b03a4fca686a3dfcc540ed4fedff |
| frozen-final.log | 2271dd0dd6e8d3e30824ca6574d775302138534210f08aca92908e67b0f0d595 |
| frozen-final.xml | 2410b561d526429ae05b89405240d9ce14c1047717a84daf8579fcc81da8a371 |
| ruff-final.log | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
| mypy-final.log | 71144743c83babea384888a735db0c4daba3d4d7b7942b6839984bd5c21b52bb |
| targeted.log | a6349489914e27cde5f1119af0759b0609b3f6ae22110368c9ced4805bde0291 |
| receipt-final-initial.log | 5a6748ae454c075b236cf05489c637669cf0fa10ecf8249627d978d681681230 |
| dag-corrected.log | 68e452547fa72d60be93b50ac7923ffcfc7209aeba9d83890aee8126dadeda37 |

Full original deadlines, fresh checks, protection/profile and grant limits remain required for any separately user-authorized future validation. No outcome beyond the local regressions above is established here.
