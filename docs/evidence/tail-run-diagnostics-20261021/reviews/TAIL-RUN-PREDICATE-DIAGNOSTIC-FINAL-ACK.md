# Tail diagnostics: final limited build/source/evidence ACK

Result: LIMITED_DIAGNOSTIC_SOURCE_AND_SYNTHETIC_EVIDENCE_ACK. Earlier source P2 and callback-test evidence refinement are closed. No open product/diagnostic P1/P2 identified in the reviewed final bytes. This is not an execution/window/grant ACK and not evidence of a completed Mock/G0 prefix.

Baseline: `d665c69074e3d97c3332e65a933bb0eaa4dd118d`.

Final SHA256, independently read and equal to callback-before/after:

- scripts/diagnostics/g0_tail_observer.py: `b23c45591ca71b98d04a3c38fa5ccaf0141adf66476edae31ee33b37e8efc4a8`
- scripts/diagnostics/g0_stage_observer.py: `adacdff642f9dc30693df817c49c28e87114a14e813d7143e323ed14eab00d03`
- scripts/diagnostics/g0_prefix.py: `dfe1299c28746db393afa3c26340c87792e7b39d665548f093c1b472151647d4`
- tests/test_cold_tail_diagnostics.py: `f60cc0865a42070cdfd2b7f10ce93f13f96b63d888498dfcb6e98cb146c780be`

Product src diff is empty. Default StageObserver remains five buckets/twenty metric rows; only the explicit existing candidate selection enables four additional tail regions and launcher-only wrappers. Original predicate/body/context functions are delegated once, with original arguments/at/guard and exception/suppression behavior preserved. No new SQL, business clock, guard replay, model dump, payload serialization, authority, cache, skip flag or public configuration was introduced.

Safe-storage closure: exact small dictionaries validate all exact string keys before lookup; type tests use identity. Bounded exact numeric primitives precede deadline arithmetic. RowMapping projection reads bounded exact tuple/index storage and ignores foreign hidden keys without hashing/equality, using only exact string/known quoted-name indices for the selected fields. Error message access is limited to the exact known DomainError's safe storage; foreign exceptions/prefixes/boundaries do not introduce descriptors/equality. Unsupported representation yields incomplete evidence while the original exception is bare-raised. Failure readback remains explicitly post-exception argument evaluation, not original short-circuit trace or unique-cause proof.

Tail metrics remain four fixed spans. Second-commit timing/counters include recheck; the separately named residual subtracts only observed recheck and is invalid if incomplete/inconsistent. Metric rows belong to the innermost active stage, preventing recheck codec metrics from being duplicated in the second_commit row. Scope proxy delegates original exit once with its original exception triple and returns the original suppression object. Diagnostic faults cannot replace original business return/error and force final diagnostic classification UNKNOWN via record_tail. Instrumentation has nonzero overhead and creates no unchanged-observer performance comparison claim.

Author-produced originals read under `/tmp/sim2act-tail-diagnostics-20261021/`:

- frozen-final.log/XML: 66 passed, zero failure/error/skip, pytest 10.56 seconds / JUnit 10.559 seconds. Before/after hashes identical. This batch used final three diagnostic modules above and the preceding test SHA `bd4c67e4eb9af50725b1de9feafce63990d1dbe7857cc0f089a02d038def4fb0`.
- frozen-observers.log: 48 unittest total, 44 passed/four optional VFS skips, 0.597 seconds, no failure/error. Original observer default-shape assertions are retained. Ruff passes.
- Afterward only the selected tests gained external callback side-effect counters and a real RowMapping armed foreign-index probe. callback-final.log/XML: nine passed, zero failure/error/skip, 25 deselected, pytest 0.18 seconds / JUnit 0.176 seconds. callback-before/after and disk bind the final four SHAs above; Ruff passes. The unchanged diagnostic modules were not rewritten or rerun through another prefix. This is not 75 distinct cases and not a full 66-case run on the final test-file version.

The external counters close the prior false-positive risk: forbidden callbacks append markers before pytest.fail, and empty marker lists are asserted outside the observer's BaseException catches. Therefore even a swallowed pytest.fail cannot satisfy the no-callback assertion. The armed RowMapping hidden-index hash/equality probe likewise requires an empty external list, while the supported safe projection still yields the expected comparison/deadline values.

Initial evidence remains historical: 25-pass first tail test batch; old stage-regression batch had seven passed, one failed and one error because the initial code changed default metric shape. The optional-tail correction retained the old assertions, and the final observer batch passed them. The earlier reports remain originals and are not relabeled as final hashes or green runs.

All results above are the author's local synthetic tests read by the reviewer. Reviewer ran zero product imports/tests/DB/Worker/Mock/G0/launcher, made zero repository writes and created no grant/window. Actual last G0 remains UNKNOWN at the second commit's composite Run predicate; this diagnostics build neither determines that historical unseen false conjunct nor authorizes a fresh execution.
