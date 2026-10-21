# Qualified C route: complete synthetic A/B result ACK

**ACK — the recorded single frozen configured synthetic semantic-clock A/B passed.** No concrete evidence inconsistency or additional P1/P2 blocker was found in this result review. This does not establish real-clock G0/PB success, production source qualification, a general performance guarantee, or permission for another run.

Reviewer activity was limited to reading source, JSON/XML/logs and file hashes. Reviewer product/test/DB/Mock/G0 executions, repository edits and signals: **0**. The SQLite files were not opened. This report supplements `C-NATIVE-QUALIFIED-ROUTING-FINAL-CODE-ACK.md`; it does not rewrite earlier intermediate reviews as reviews of the final hashes.

## Recorded execution and exact comparison

The author-run log and JUnit agree: **1 passed, 0 failures/errors/skips, 117.39s** (JUnit suite 117.394s). `qualified-pair.json` classifies the result `CONFIGURED_SYNTHETIC_SEMANTIC_CLOCK_NOT_G0`. The single shared fresh prefix and two isolated restored Cold cases consumed **7 Mock exchanges / 9 method entries / 2 Source delegates**. The three recorded exchange files contain 5, 1 and 1 lines. No automatic retry, real model, Cold2 or W5 is represented by the passing harness.

The reviewed harness actually asserts, and the report records for each arm, real preparation, first and second commit return, receipt production, original context/scope normal return, inactive scope/mode and rejection of a subsequent closed-scope check. The final original clock sample is virtual `1800000300`, below its minimum captured deadline `1800000330`; both arms' final samples match. The test's TailStop terminates after the original context returns and before W5. This is complete execution of that protected semantic tail, not business completion after W5.

Both arms preserve:

| Observation | Python | Qualified C |
| --- | ---: | ---: |
| SQL statements, full ordered parameters compared | 7735 | 7735 |
| Run predicate calls | 2 | 2 |
| Base calls / returned / rejected closed-scope probe | 569 / 568 / 1 | 569 / 568 / 1 |
| Qualified base calls | 275 | 275 |
| Base dynamic checks | 1137 | 1137 |
| Complete observed codec calls | 8062 | 8062 |
| Codec returned bytes | 4,682,215,371 | 4,682,215,371 |
| Native selections / Python selector fallbacks | 0 / 0 | 8038 / 0 |

Candidate reasons are exactly `eligible:8038`. This confirms the C route was used in this chain; it does not turn all 8062 codec calls into 8038 native projections. The original Python storage helper identity is asserted unchanged, and both arms retain the same base qualification. The final source freeze contains the six files from the code ACK; their current bytes independently match it, including adapter `f3560608…`, C `c1b0f487…`, runtime `c0622686…`, and A/B test `6e777508…`.

Independently hashed strict output, ordered SQL/parameter and receipt files match byte for byte across the two arms:

* `strict-output.json`: `52926c4a1446ae0b6d3d2bea8bfe47f9578011c1216c712d4dc887d13a4cec2a`
* `strict-sql.json`: `fb9db5859c85e951df9833b9f6be43048ee6c66689417d84621c550995858a6d`
* `strict-receipt.json`: `984c02018f9f628bca94e11b5ff6172576a03b92f48089fa5b1d53c4b8a1c434`

The receipt witness is precise: original Cold run/reader/pending/proof-index binding, complete outputs/proved payload, original binding object identity and audit fingerprint, with stored receipt fields. It is not a second serialized copy of the entire mutable source binding. Existing source/CGR/SQL checks remain the authority; the test does not replace them with a receipt identity assertion.

## Timing and cleanup limits

The same measured interval is `worker.once()` through the pre-W5 TailStop, with the same observers in each arm and no profiler. Owner CPU was `43.732164740` versus `43.032715942` seconds; the observed difference is `0.699448798` seconds (approximately 1.599%). Wall times were `43.994863476` and `43.315996060`. This is one ordered A/B observation without statistical replication. It is not the earlier approximately 33-second context-only interval, does not demonstrate stable whole-tail speedup, and cannot be used to infer a real 30-second lease outcome from this semantic-clock test. Local component medians and this full-tail measurement have different scopes.

The harness runs per-case close/teardown and asserts no newly introduced live threads after both cases. The final report records `cleanup_threads_empty=true`; the source inspection confirms these assertions are reached before result publication. A read-only file listing found no SQLite sidecar files under the completed A/B directory. The review did not independently scan current processes or open databases. The author's observed directory size is not a hard disk quota or RSS bound.

## Original result hashes

* `/tmp/sim2act-c-qualified-20261021/qualified-ab.log`: `7f68a42aa7092bd6233871b309a0b9bf7adb109f3c70a6eebe12006694571b5c`
* `/tmp/sim2act-c-qualified-20261021/qualified-ab.xml`: `0ea14f929ba6ac8268909278aeb9c5af880604309931aa519d39ff5eb52d1308`
* `qualified-ab/test_final_qualified_native_pa0/qualified-pair.json`: `fd2354395d14acd59406cc134055890fa7f27036e9126c933239bf33180f073d`

The passing result adds this finite configured semantic A/B evidence to the already reviewed bounded selector and negative unit cases. Defaults remain Python; the candidate remains an explicit exact-build, test-only SQLite route. No additional test, Mock exchange, G0 window or new requirement is requested by this ACK.
