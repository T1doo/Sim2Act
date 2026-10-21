# Tail observer frozen closure review

Decision: **ACK — diagnostic-only code and stated local test evidence**. No remaining blocking finding was identified in the four frozen files below. This is not a G0 run, performance acceptance, native allowance qualification, account qualification, grant, or approval to open another window.

Baseline HEAD: `d665c69074e3d97c3332e65a933bb0eaa4dd118d`. The reviewer read source/diffs and author-produced logs/XML/manifests and independently recalculated file SHA-256. The reviewer did not execute code, tests, SQLite, product, Mock, Worker, models, launcher windows, profiles or signals; did not alter repository files. Only this `/tmp` review was written. The actual code reviewed and author test executions are bound to the four hashes below; parent remains the sole repository writer.

## Closed findings and behavior

- Failure metadata now uses identity-only type gates, fixed-size dictionaries with native-string keys, field-specific native text/number limits, and the bounded known RowMapping data/index representation. Foreign model/metaclass/key/prefix/boundary/exception descriptor callbacks are excluded from the diagnostic route. Number validation precedes deadline arithmetic; unsupported or out-of-diagnostic-domain data makes evidence incomplete rather than changing product acceptance.
- The original Run predicate is called first, exactly once. No guard, `_trial_result`, SQL, fresh business clock, model dump, extra graph walk, hash or codec replay is used for failed-comparison metadata. The exception is bare-reraised; diagnostic faults cannot replace it. The report correctly labels comparisons as post-exception reads using original `at`, not original short-circuit execution or a unique cause. An exact message match identifies the message only, not the source of a uniquely false predicate.
- The original commit-prefix type is checked before reading its key. Prefix boundary comparison is restricted to native strings. The target wrappers preserve the original call on bypass and diagnostic selection faults.
- The scope proxy delegates the original `__enter__`/`__exit__` once, with original exception triple and exact exit result. It is nested inside the existing selected context/StopBoundary, so successful original scope return remains distinct from the deliberate outer G0Stop. Enter failure, body exception, exit exception, suppression and observer clock faults do not create an alternative product control path.
- Four fixed tail buckets cover second prefix, second commit inclusive, nested recheck and scope exit. Wall/thread CPU and original check/input-key counters use deltas. The derived remainder subtracts **only observed recheck**; it is not all-child exclusive CPU. StageObserver's tail codec/other metric rows use the innermost region, so the second-commit metric row already excludes recheck calls. Successful codec returned-byte totals require no additional serialization/hash. Unreached is represented by `calls=0`; failed/invalid measurements cannot prove completed scope or deadlines.
- Default StageObserver retains five stages/20 metric rows; explicit candidate instrumentation opts into nine stages/36 rows with the same bounded stack. Product `src` diff is empty. No lease, SQL/auth/fence, full validation, runtime budget, launcher protection, Mock count or window contract was changed.
- `record_tail` runs only when archiving evidence after original work/unwind. INCOMPLETE, malformed or throwing tail report makes diagnostic classification UNKNOWN. It does not change the original product result/error or turn unknown evidence into success.

## Author test evidence, read only

Final `frozen-final.log` reports **66 passed**, one existing Starlette deprecation warning, **10.56 s**. JUnit independently states tests=66, errors=0, failures=0, skipped=0, time=10.559. It includes 33 tail cases plus existing admission-diagnostic, launcher-ready and Mock-wiring local suites. These are diagnostic/local tests, not a complete Cold prepare/commit or G0 execution; the tail suite includes a separate in-memory SQLite RowMapping-storage control, which the reviewer did not run or open.

`frozen-observers.log` reports **48 total = 44 passed + 4 explicitly skipped**, 0.597 s, successful exit. The four skips still require the separate optional compiled native unit dependency; they are not passes. The old default five-stage tests now pass without removing their assertions. `ruff-final.log` says all checks passed. The before/after manifests and independently read current hashes agree for all four files; `src` diff remains empty.

The initial 25-pass/0.19 s evidence is preserved as the initial version only. The subsequent old-stage regression remains **7 passed, 1 failed, 1 error**: unconditional tail expansion changed the default shape. It is not relabelled successful. Final opt-in expansion and final tests supersede the defect for this frozen implementation, while preserving the original failed log.

No new window was run as part of this slice. Instrumentation has nonzero timing/scheduling overhead. This review cannot forecast a 30-second lease outcome or resolve the previous compound Run rejection without a separately authorized, frozen execution and actual evidence.

## Frozen code SHA-256

| File | SHA-256 |
| --- | --- |
| scripts/diagnostics/g0_tail_observer.py | b23c45591ca71b98d04a3c38fa5ccaf0141adf66476edae31ee33b37e8efc4a8 |
| scripts/diagnostics/g0_stage_observer.py | adacdff642f9dc30693df817c49c28e87114a14e813d7143e323ed14eab00d03 |
| scripts/diagnostics/g0_prefix.py | dfe1299c28746db393afa3c26340c87792e7b39d665548f093c1b472151647d4 |
| tests/test_cold_tail_diagnostics.py | bd4c67e4eb9af50725b1de9feafce63990d1dbe7857cc0f089a02d038def4fb0 |

## Final evidence SHA-256

Evidence root: `/tmp/sim2act-tail-diagnostics-20261021/`.

| File | SHA-256 |
| --- | --- |
| frozen-final-before.json | ee5df1258b8ce6edf46d9bc3a09832db30360fe4a7e08fa71baab280c0394423 |
| frozen-final-after.json | 8ba50b30a648407efe5ea4e1b071a75b480d486739101e680d98aef1dc6bcca5 |
| frozen-final.log | 08142eb074d21abdde984e1e19546d0cd493f9aea16918c2d9680a72c4115770 |
| frozen-final.xml | 646c84cac8464463c5a66101bb6abbcc99f4df326efd78d61c9083db98813642 |
| frozen-observers.log | f305b115154888672024cb9c8eab75e62209312213d5742dd204749fc1c85904 |
| ruff-final.log | 82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18 |
