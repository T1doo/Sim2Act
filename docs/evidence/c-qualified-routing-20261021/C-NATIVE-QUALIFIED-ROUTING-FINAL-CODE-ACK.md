# Final qualified native routing: limited code and unit-evidence ACK

Decision: **ACK_CODE_AND_BOUNDED_SYNTHETIC_AB_TEST_DESIGN**. No remaining concrete P1/P2 blocker was found in the reviewed frozen implementation. This is a review conclusion, not a new execution grant, production qualification, real-clock G0 result, or an assertion that the pending complete A/B has already passed.

The reviewer only read source, Git/file metadata and the author's recorded outputs. Reviewer execution of product code, tests, SQLite, Mock, Worker, G0 and launchers: **0**. No repository changes or signals were made. Reports were written only under `/tmp`.

## Frozen bytes

| File | SHA256 |
| --- | --- |
| src/sim2act/_cold_typed_native_impl.c | c1b0f48779febbfcec6e9316c8f27f31bff34f926eb667cdfa1a5b173d51ce2d |
| src/sim2act/_cold_typed_native_candidate.py | f356060885d0ab74edf7817732d72e69d54ff55d4a76b94d14df56f268fabd05 |
| src/sim2act/natural_spec_runtime.py | c06226860b7690daff210be62e69433eb2a174f4a63b90ba3d18304b2fca0f12 |
| scripts/build_cold_typed_native.py | 2a06690d178a85b891d52eede59a38caa5c6fcba14c85b893fb31aa3276f3d10 |
| tests/test_cold_typed_qualified.py | 6fe74952d1feae9aa5a8e3fe5459e436df8b16f7d2455fc6c24eeae36fc0bc39 |
| tests/test_cold_qualified_native_pair.py | 6e777508041d9ab8a09cc4f37538841c141a45f3ba9e6d9f03eb37fd445122ef |

Earlier adapter SHA values, including dbbfac95 and 415ed289, are intermediate reviews. This ACK binds the actual final f3560608 file containing both independent binary allowlisting and the ASAN preload gate.

## Findings closed

* Original-frame `input_bytes` invokes the loader-issued builtin C `stack_ready` before adding selector/catalogue Python frames. It only reads remaining counters, with a conservative 128 floor. A low-stack fallback returns to the original frame before calling the original Python storage helper. A native projection exception is propagated once, never retried through Python.
* The selector freshly scans exact native values and approved model layouts. It verifies native namespace keys before lookup, exact standard metaclass, inherited builtin storage descriptors and bounded member offsets. Missing/unsupported metadata, cycle, depth and work bounds select Python before native projection. Actual callback or allocation exceptions are preserved rather than cleared as an absence signal.
* Namespace ownership is now explicit: cached `PyType_GetDict` new references are retained and released, duplicate references are decremented, and the separately acquired own namespace is released. The author's refcount regression is finite evidence for the discovered leak; it is not a universal leak proof.
* Qualification and projection share a C call. The accepted graph has fewer than 256 visits, stays below the copier's internal signal-poll interval, dispatches no user getters/iteration/hash/equality, does not release the GIL, and does not alter GC or recursion counters. The exact-build CPython GC scheduling distinction is essential; this is not an argument that the GIL alone proves arbitrary C/Python purity.
* The loader checks an independent fixed release/ASAN binary digest before importing, in addition to the executable, source, headers, ABI, command receipt and embedded identity. It rejects an ASAN binary before importing when the expected existing ASAN runtime is absent from process mappings. This remains a local known-build integrity contract, not a sandbox against arbitrary native binaries or concurrent hostile file replacement.
* Runtime attachment is explicit and restricted to test-only SQLite workers. The original storage helper identity and default Python route remain intact. Raw `project` stays an offline primitive with known all-domain recursion differences; only the bounded selector supplies the reviewed runtime route.

The relevant CPython mechanics were checked against [3.12.14 GC source](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/gcmodule.c), [eval-breaker handling](https://raw.githubusercontent.com/python/cpython/v3.12.14/Python/ceval_gil.c), and [recursion internals](https://raw.githubusercontent.com/python/cpython/v3.12.14/Include/internal/pycore_ceval.h). These exact-build conditions must not be silently generalized to another interpreter.

## Author-run evidence read

* `final3-unit.log`: ordinary build, 43 passed / 11.61s; before the final added metaclass-descriptor case and loader refinements.
* `final-asan-unit.log`: 44 passed / 14.56s, same C implementation, with the added descriptor case. Only the extension was instrumented; `detect_leaks=0` does not establish LSan or whole-interpreter memory safety.
* `final-qualified-pinned.log` and XML: final loader/selection cases, 12 passed / 6.38s. They overlap prior runs and are not added as 99 distinct tests. Low-stack/namespace/descriptor/alias cases and source routing are finite tested cases, not proof over all CPython extension behavior.
* The final local net-cost observations, including qualification, report medians Python `0.125379793` and qualified `0.098803690` seconds for 1000 copies plus original pickle, native 5001 / Python selections 0, with PB visits 227/work 2479/required stack 92. This is approximately 21.196% for this component/input and benchmark setup. It does not predict whole-tail CPU or G0 success. Earlier 22.48% and 18.93% development observations are not the final result.

Recorded log SHA256:

* final-qualified-pinned.log: 33b5749d61e7663f6b4ce1c0fc171c6c213c974b519cb2825aa5920989311c75
* final-qualified-pinned.xml: 6b484a0f714e3d0089c06041cd29bc73b7edcf0aab0143ec61cc05e382af50f8
* final3-unit.log: a7f28c33c0a15dc5430d0c524efa7be793fa55a3d11795fca13a73973736fb1d
* final-asan-unit.log: 37c0b6e6ac9ad45af5f904a6d154165c17f545b2a2c1b47688dc9501077ad67d

## Pending A/B boundary

The reviewed harness uses one fresh configured synthetic prefix and two isolated restored Cold cases, with cap 7 Mock exchanges / 9 method entries established before prefix creation. It attaches the verified release backend only to the candidate worker and compares complete strict outputs, ordered SQL/parameters, exact receipt payload/identity witnesses, original final samples, base qualification, dynamic counts, and complete codec counts/bytes. Both arms must execute two original commits, receipt production, normal original scope exit and closed-scope rejection, then stop before W5/Cold2. The harness requires native selections in the candidate arm, zero selections in the Python arm and preserved 275 base qualifications.

Its successful execution has **not** been observed by this ACK. Root must bind execution to its final complete source/test/dependency freeze, exact release binary and user-authorized 600+10 bound, and independently preserve cleanup/results. A passing result would establish a configured synthetic virtual-clock semantic comparison, not production source qualification, real-clock G0 performance, complete PB, or lease changes. This reviewer neither grants nor starts a window.
