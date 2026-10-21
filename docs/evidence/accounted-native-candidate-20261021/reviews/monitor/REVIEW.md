# Native accounted candidate: independent static review

Decision: **ACK_DEFAULT_OFF_STATIC_CANDIDATE_ONLY**.

The reviewed candidate remains explicitly selected, pre-origin and test-only SQLite. This ACK covers the frozen implementation's stated producer/consumer domain; it does not approve installation, a new execution window, or removal of unrelated mutable-frontier checks.

## Scope and evidence

Read-only source, diff, existing raw logs and SHA256 inspection. The reviewer did not run tests, open databases, execute Mock/model/Worker/G0/native prepare/commit/profile, signal processes, or modify the repository. Only this independent `/tmp` report was written.

Base HEAD: `6570b7072e3cd415fbbcb3a130e8a80d9ad8be79`.

Six actual file hashes matched `/tmp/sim2act-native-candidate-20261021/closure-hashes.json`:

| File | SHA256 |
| --- | --- |
| src/sim2act/_cold_accounted_native.py | 0b69626b90e7078ef310227fc49d9813ee6c6d60d4d7657ba21c51cc3b6b4864 |
| src/sim2act/_cold_accounted_values.py | 4c518ea5a389f6f68c000d2fac47c79ffc4906a090bb03dc199e9c60b88f94fc |
| src/sim2act/cold_accounted.py | 9d02e05d7059b03408145d5e4a802bdce4df48991dd7b601a2fbc07ecea173d1 |
| src/sim2act/natural_spec_runtime.py | 77907505b42d1e46cc8d133b91a2349ebdd5c2df8b06d6a398bde668a82130e6 |
| tests/test_cold_accounted_native.py | 23bab4408a66cb50fe494d45000037b48a6da437f6ec3e183365497cdf071444 |
| tests/test_cold_accounted_component.py | 16abcb5a07162a24cf9451e468008dc046cfeb5eda1d35d53ab6899182e5d735 |

## Resolved findings

- Source and Generate stay at their original positions, separated by the original recipe/backend-version checks. Staging does not call either producer again; joint selection precedes publication, with no fallback after issuance.
- Family access crosses the original exact scope/role/root checks before arena lookup. Canonical lookup crosses `_source_parts` before hashing an aid. Arena comparisons require exact Nodes, the same ledger, and registered packets.
- The immutable structural interner preserves container/scalar tags, dictionary order independence and quoted-key text semantics, quoted-value tags, float signed-zero equality and alias-independent value equality. Full native keys are compared on hash collisions. It does not use a digest or identity as a value-equivalence proof. Runtime arena comparison has no generic allocating `_equal` fallback.
- Node/children/Value/Record/Family accessors are built before publication, then tables become mapping proxies and usage becomes a frozenset. Scope, transaction, current binding and remaining mutable inputs continue through their live checks.
- RowMapping visible comparison does not create the old full row-storage projection or a visible dictionary. Per-call completed comparison memo retains strong original references; active tracking uses the original object.
- Receipt/proof exact dictionary lengths (18/7) precede key iteration. The fixed real resolver output is checked in full, including unused fields, with exact scalar/container types and native-domain/cycle/nonfinite gates. This restriction is confined to the private native producer output; default helper behavior is retained.
- The fixed twelve later roots are explicitly enumerated. Up to two additional exact Release-pointer keys are derived from the same bounded copy of already pinned bound facts, with matching snapshot/release IDs and reservation before string construction. Their SQL remains at its original location, with original authorization and complete fresh serialization. No prefix wildcard or rebinding is allowed.
- Sizing inherits row depth, checks completed memo longest paths, and treats nested SQL carriers as a pre-issuance optimization limitation. Data-dependent sizing copies/memo and comparison snapshot locals are dropped before their tickets close.

## Budget interpretation and remaining limits

The claim is a conservative logical allocation/work budget for this closed candidate protocol, not RSS, live Python heap, CPU instructions/timing, allocator availability, or a whole-G0 bound. Class interning is prepaid before construction, uses linear resident structure with dictionary sorting work, and does not create an all-pairs equivalence table. Later scratch is scoped to the fixed SourceBodies two Slot comparisons plus Archive two Slot comparisons, one fixed resolver receipt and two body tuples; two independent first-boundary maxima are reserved, although the actual second continuation does not replay the archive. Full Ledger and remaining-frontier admission measurements, fixed mirrors and known byte-derived initialization are included. Original SQL/decoding and unrelated full checks retain their explicitly separate scope.

Nonblocking wording correction: `_FIELDS['identity']` currently has 14 fields. The implemented `len(...)` formula evaluates `slot_nodes` to 53, conservatively exceeding a fully expanded 51-node Slot tree. The nearby 15-fields/55-node comment is stale; evidence should cite the actual formula/value rather than claim 55 was reserved.

Earlier frozen raw regression was **333 passed / 3 failed**, with unexpected lazy Release-pointer roots and a caller-list test omission. It is retained as failed evidence, not reused as final success. The closure target and final full regression were pending at this review; no pass count is asserted for the final six hashes here.

Native `_prepare` and both actual commit continuations have not been executed by this reviewer. Source fixtures and SQLite core tests do not establish full binding/prepare/commit integration, production-scale qualification, install approval, or any G0 speedup. Final consistent-hash test logs must be reviewed separately.
