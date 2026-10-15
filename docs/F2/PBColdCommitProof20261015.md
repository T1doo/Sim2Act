# Cold commit proof continuation — 2026-10-15

**NOT_ACCEPTED.** The normal offline Cold flow and all requested individual fault/cache/qualification cases have passed on the final production bytes, but a same-production-code pre-send failure remains unexplained. The later five fault passes do not establish a repair of that failure or stable reliability.

Base is `bb04afc3d42c0565ffe9adf1d076ef7af182ab95`; branch is `dev/pb-cold-commit-proof-20261015`. Final tested source/test commit is `d798e825e48d50ed7733739f1bee2c80d7885b31`. Production src/pyproject is byte-identical to `a027e9a10ae5d19dff6b373be7e982847a6d3846`; d798 only adds original public failure-receipt capture to the fault test. The final delivery commit adds this report and evidence only.

The one bounded baseline observation found repeated full stage/source proofs inside ten public Cold check_commit windows of 5.3367–6.8257 seconds. Nested windows overlap; these are public elapsed windows, not exclusive CPU/helper/lock-owner attribution. No second profiling observation or private SQL/UDF was used.

`natural_live_admission.py` and `natural_source_archives.py` now continue the already completed full source/bound proof within the same synchronous call for exact ordinary offline SQLite lineages. `app_jobs.py`, `pa_spec_apps.py` and `pb_natural_specs.py` pass an internal output from the actual read_release origin verification to avoid its immediate duplicate. Continuation requires the same transaction, driver, thread, epoch, Limits, user/source identity and current authority. Missing/mismatched/special paths retain the original complete proof. A cache-hit callback changing the read segment or Limits explicitly takes the full original fallback. Nothing is reused across guards or writes.

Input schema checks, fresh current authority/source pointers, complete first source/output/archive/accounting proofs, original atomic writes, lease/fence/version/deadline/consent and budget checks remain. Worker/db/trial-dispatch/budget/runtime/anchors and original normal/extraction/cache assertions remain unchanged. Qualification pins the exact reviewed 86-module closure, retaining the original anchors and CHANGED set.

| Batch | Exact executed SHA | PASS / FAIL / ERROR / SKIP / interrupted | RC |
| --- | --- | --- | --- |
| baseline-public-chain | `bb04afc3d42c0565ffe9adf1d076ef7af182ab95` | 0 / 1 / 0 / 0 / 0 | 1 |
| candidate-cold-and-faults | `d94c773e1ddd1fff4568b5e9f1d91a63d6fb5d2c` | 15 / 2 / 0 / 0 / 1 | 2 |
| cold-and-faults-conservative | `a027e9a10ae5d19dff6b373be7e982847a6d3846` | 16 / 1 / 0 / 0 / 0 | 1 |
| cold-refusal-public-errors | `d798e825e48d50ed7733739f1bee2c80d7885b31` | 5 / 0 / 0 / 0 / 0 | 0 |
| final-source-exact | `d798e825e48d50ed7733739f1bee2c80d7885b31` | 22 / 0 / 0 / 0 / 0 | 0 |
| qualification-first | `d798e825e48d50ed7733739f1bee2c80d7885b31` | 12 / 0 / 0 / 0 / 0 | 0 |
| qualification-second | `d798e825e48d50ed7733739f1bee2c80d7885b31` | 10 / 0 / 0 / 0 / 0 | 0 |
| source-cache-and-origin-conservative | `a027e9a10ae5d19dff6b373be7e982847a6d3846` | 22 / 0 / 0 / 0 / 0 | 0 |
| source-cache-and-origin-final | `4464486a6d4674c6cc5ce78c8b99d3d5892d5df1` | 13 / 1 / 0 / 0 / 0 | 1 |

The a027 batch really passed normal Cold plus six stage and nine extraction cases (16 PASS), then failed source_revoke before its expected send/injection; its four remaining faults were NOT RUN. The normal receipt records seven accepted slots, 7000 settled tokens, fourteen request/response archives, two actual offline Cold sends and original intervals. The later d798 five faults all have actual requested injection and one send; source_revoke records GRANT_REVOKED, WAITING_RESOURCE and HTTP403, with no accepted result. These are separate batches; there is no all-green single integration run.

The final exact d798 source run has 22 PASS: the original fourteen cache counterexamples and eight internal origin-boundary cases. Qualification was split 12+10 to bound disk use, all 22 PASS. Six stage-boundary cases and nine extraction cases executed at a027 have unchanged fixture/node AST at d798. Every batch retains command, exact Git SHA, 503 source/test hashes, original XML/logs, import policy and losslessly packed fixture/source bytes. Generic source-fixture tests use actual Worker Generate3/Source2 with MockTransport; they do not establish live seven-slot quota coordination. A legacy fixture receipt field about unchanged lease timestamps means no manual override, not that Worker never naturally updates leases/fences/status.

All failures remain retained: baseline normal RUNNING failure; d94 normal failure, HTTP source-read assertion failure and one explicit SIGINT interruption; 446 cache Limits callback count failure; a027 pre-send source_revoke failure. The callback regression was fixed with conservative full fallback and original assertions retained. The a027 pre-send failure is unresolved. Earlier full389 remains 388 PASS / 1 FAIL / RC1 / NOT_ACCEPTED; peer_version is not fixed here.

Ruff actually PASS (RC0). Mypy actually ran on final d798: RC1, five existing errors in unchanged status_report.py (3) and tools.py (2), 87 source files checked. It is not green. No real model/paid API calls, LIVE remains closed. PG, Windows, native browser, human semantic acceptance, complete live P-A/P-B, old database upgrade and remote CI are NOT RUN. No credential/security permission expansion, deployment, force push or main/core modification occurred.

Independent static/execution reviews are in archived `review/`, including FINAL_REVIEW.md. Evidence fidelity is approved; product stability/overall acceptance is not. Complete evidence is sealed under `docs/evidence/pb-cold-commit-proof-20261015/` with MANIFEST.json, ARCHIVE.json and cold-commit-proof-evidence.tar.xz. Original prior reports/evidence and unrelated WIP remain intact. Exact final push/remote/clean/protected-ref verification is recorded outside the sealed evidence after delivery.
