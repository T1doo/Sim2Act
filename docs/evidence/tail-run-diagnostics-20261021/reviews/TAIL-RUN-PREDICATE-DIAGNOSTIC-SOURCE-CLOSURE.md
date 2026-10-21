# Tail diagnostic safe-storage closure: incremental review

Product/diagnostic code P2 closed in read frozen bytes; one test-evidence refinement remains before the final combined ACK.

Read four SHA256 values agree with frozen-final-before/after: tail `b23c45591ca71b98d04a3c38fa5ccaf0141adf66476edae31ee33b37e8efc4a8`; stage observer `adacdff642f9dc30693df817c49c28e87114a14e813d7143e323ed14eab00d03`; prefix `dfe1299c28746db393afa3c26340c87792e7b39d665548f093c1b472151647d4`; test `bd4c67e4eb9af50725b1de9feafce63990d1dbe7857cc0f089a02d038def4fb0`.

safe_dict now bounds dictionary size and validates all keys as exact strings before fixed lookups. Known types are checked by identity, not potentially foreign metaclass equality. Derived deadline arithmetic accepts bounded exact numeric primitives first; string concatenation and huge integer arithmetic are rejected as incomplete evidence. The actual finite/nonfinite comparison facts remain separate from exportable scalar availability.

The RowMapping path reads only bounded exact _data tuple and _key_to_index dict storage, scanning without hashing/equality of foreign Column/alias keys. Only exact str/known quoted_name and bounded exact integer indices enter a new lookup. This does not copy or inspect full row payloads, issue SQL or call the original row lookup on foreign hidden keys. Unsupported scale/representation marks incomplete; no general arbitrary RowMapping acceptance claim is needed.

Prefix/second-commit selection now gates exact known prefix class and safe field dictionary; boundary equality is exact str only. Original exception message is read only for the exact known DomainError using safe storage; other error type names use the base type getter rather than a foreign descriptor. Metadata cannot replace the original exception. record_tail runs after original execution/unwinding and turns diagnostic failure/incomplete/unsafe report into UNKNOWN; default disabled reporting retains its classification.

Read author originals: frozen-final.log/XML show 66 passes, zero failures/errors/skips, JUnit 10.559 seconds; final four hashes unchanged. frozen-observers.log shows 48 unittest total, 44 passes/four optional VFS skips, 0.597 seconds, no failure/error; ruff-final.log passes. Earlier 25-pass initial and seven-pass/one-fail/one-error default-shape stage regression remain separate historical evidence.

Remaining test-only evidence issue: the new foreign-metaclass/colliding-key probes call pytest.fail from a forbidden callback, but the observation wrapper deliberately catches BaseException and marks incomplete. If the callback were mistakenly invoked, pytest.fail could be swallowed and the current expected incomplete result could still pass. Foreign prefix/boundary probes have a similar risk. Add a side-effect list in the forbidden callbacks and assert it remains empty after the original exception is observed; a focused rerun of those existing cases is sufficient, no repeat of the whole 66-case batch is requested. This does not imply a remaining source callback path was found after the safe-storage fix.

Reviewer performed read-only source/evidence analysis, no product/test/DB/Worker/Mock/G0/launcher execution and no repository write. No execution/window/grant ACK is created by this incremental source closure.
