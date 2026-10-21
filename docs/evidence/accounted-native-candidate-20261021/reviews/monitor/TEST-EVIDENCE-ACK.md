# Final native candidate test evidence: independent read-only ACK

Decision: **ACK_RECORDED_FROZEN_OFFLINE_REGRESSIONS_ONLY**.

This is a supplement to `REVIEW.md` and does not replace or expand its default-off static implementation ACK. The reviewer only read other people's test/check artifacts, compared file SHA256 values, and read the archive README. The reviewer did not execute tests, product code, databases, Mock/model/Worker/G0/native prepare/commit/profile, or signals, and did not modify the repository. Only these independent `/tmp` evidence-ACK files were written.

## Observed final artifacts

Archive: `/workspace/Sim2Act/docs/evidence/accounted-native-candidate-20261021/`.

- `tests/verified-pytest.log`: **337 passed, one existing Starlette deprecation warning, 184.00 seconds**. Matching JUnit header: tests=337, failures=0, errors=0, skipped=0, time=183.998 seconds.
- `tests/closure-pytest.log`: **66 passed, the same existing warning, 46.92 seconds**. Matching JUnit header: tests=66, failures=0, errors=0, skipped=0, time=46.924 seconds.
- `checks/ruff.log`: `All checks passed!`.
- `checks/mypy.log`: `Success: no issues found in 4 source files`.
- `checks/diff-check.log` records exit 0 with no diff-check output. This reviewer did not rerun any check.
- `validation.json` agrees with these counts and reports isolated synthetic SQLite, default-off selection, no full native prepare/trial commits, no Mock/real model/G0/performance window, and unchanged source/test hashes after the final run.

The four archived pytest/JUnit files were SHA256-identical to the corresponding originals in `/tmp/sim2act-native-candidate-20261021/`. All six current source/test file hashes match the earlier reviewed freeze, `closure-hashes.json`, and archived `source-hashes.json`. The archived monitor `REVIEW.md/json` are byte-identical by SHA256 to this reviewer's original reports. The inspected manifest entries agree with the computed hashes below.

## README consistency and limits

The README accurately distinguishes the explicit, default-off, pre-origin test-only SQLite candidate from production installation or complete native acceptance. It records the actual Slot formula result 53 and receipt bound 74; twelve fixed later roots plus at most two exact scoped Release-pointer keys; original Source/recipe/backend-version/Generate order; pre-issuance whole-family selection; closed immutable arena/class comparisons; and continued fresh mutable-frontier/authorization/transaction/deadline checks.

Its budget description is confined to conservative logical allocation/work costs for the closed candidate protocol. It makes no RSS, live-heap, CPU hard-limit, whole-G0 bound, production-scale allowance, or speedup claim. The receipt/proof fixed shape is explicitly the current private producer output, not a new public string cap. Earlier failures are preserved and distinguished from final results. No substantive README error was found.

The recorded real `_graph_pb_accounting` refusal remains `LIVE_BLOCKED` for unavailable reviewed production account evidence; helper positives are not presented as production admission positives. No full native binding/prepare/two-commit or G0 success follows from these artifacts. Those integration, qualification and performance conditions remain open.

## Evidence hashes

| Artifact | SHA256 |
| --- | --- |
| README.md | 23a28d08885bb38779119e0c2c02229a2dbd6b9f49c3ebd272702e1f56fb3e30 |
| source-hashes.json | 96b894d4890cc869baa025391db3bcde84e0d5a1026878abab4ee4be01e58eab |
| validation.json | 7a0cea85ed36a06aaf91365a89a1f8c369d7faa48d8a1f21214bfd06b4dd6705 |
| tests/verified-pytest.log | 58f9c9b9e58f970f55b72985d8896d0d5daea59e69ae6c3dc02588a2f5562c19 |
| tests/verified-junit.xml | fc237d4b7955aaed1a96788a9bb4553c39d475814e4532570a64bd91ba4c11a5 |
| tests/closure-pytest.log | 0bd5266220e2723d204b6dfea04e3ecce4759ff3a9db087d77109ec2fe3058dc |
| tests/closure-junit.xml | 487e1f7a437358d336311c9916baa86e419670c3f06f91edcc97d57b8779002b |
| checks/ruff.log | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
| checks/mypy.log | 71144743c83babea384888a735db0c4daba3d4d7b7942b6839984bd5c21b52bb |

Six source/test SHA256 values remain exactly those in the original independent `REVIEW.md/json`; no code change was included in this evidence-only ACK.
