# Single content pin inside native _base — source design review

Baseline read: `a8b0a0c5de75ae494d9fc77dae2c95a6a6645892`. **Conditionally implementable in the fixed `_base` collector only; not yet a code ACK.** No code/test/product/database/Mock execution or repository edits by the reviewer.

## Exact existing boundary

`natural_spec_runtime.py:2489` currently performs full CGR → `_typed_parameters()` → full CGR, then invalidates on any exception. `_typed_parameters` has exactly this one source caller (`:2494`); public guard/assertion contracts need not change. Its issued native branch already uses private pure family/stage predicates with cheap `_base_parameters_current` witnesses on both ends (`:2504–2625`, `cold_accounted.py:717–751`). Legacy/non-ready paths must remain the existing implementation.

`_ColdGraphRead.check` at runtime `:1822` combines the dynamic lifecycle/header/source-read checks and the final full `input_key`/native frontier codec. Extracting the former into a private method is reasonable if public `check` retains its original order, count convention, exception invalidation and complete content check. Do not replace CGR's raw/hidden RowMapping storage pin with a visible typed projection.

The fixed collector includes journal revision comparison; owned Source/Generate family identity; trial/generation/extraction/use/release exact classes and identity joins; both nine-field stages; frozen/extraction/raw comparisons; admission original/expected; source verification result; and RunCheck. Keeping only two scalar/model roots would be insufficient. `_trial_typed_values` (`natural_live_admission.py:1340`) still executes serializers, including fallback arbitrary replacements, so it is not unconditionally pure.

## Smallest promising qualification route

Keep one private native-only lexical route in `_base`, with no skip flag, PASS token, cross-call cache, public/env configuration or relaxed independent reader. Require exact ready NativeCandidate/OwnedMode plus original owner/graph/arena/ledger/phase/test-SQLite joins. Retain both cheap dynamic/links endpoints and complete exit content validation before returning any value.

Qualification need not traverse all CGR roots. The collector only needs callback-free structural reads to assemble the actual lexical model/raw triples. Complete actual DFS already performed by `_Comparison.validate_model` discovers every reachable fixed model, including nested Any fields. Its invocation-local model list can supply the reached classes for code-purity qualification. Check each actual class once per invocation; traverse that class's live schema/code metadata freshly. This is a code-configuration witness, not cached input validation. Do not scan the entire catalog for every cohort or cache qualification across calls.

Runtime already imports `_cold_policy_segment` at module scope, so its original `_SCHEMAS` witness is available before this `_base` path. Its fresh `_fixed_schema` (`_cold_policy_segment.py:77`) checks complete schema shape, original serializer/validator and static constructors. Reusing that reviewed principle is narrower than adding a second bootstrap registry. `_Comparison.standard_serializers` alone (`_cold_typed_stream.py:257`) proves constructor-schema identity but does not detect in-place changes to that schema object. Descriptor `model_dump`, same-extension-type replacement serializers, changed schemas, unsupported types and any unknown nested model must choose the original full-pin path before any unqualified serializer executes. Preserve the existing fixed serializer call and full actual/raw/dump comparisons.

Before a root mapping membership or lookup, require exact dict and inspect all keys without hashing/comparing foreign keys. For root qualification, exact-str keys are a cheap conservative criterion; trusted quoted names may simply retain legacy behavior. Every consumed nested mapping must still pass the existing `_trial_pure_mapping` safe projection. That function (`admission.py:1230`) gates keys before lookup and the RowMapping helper scans foreign index entries without their hash/equality. Do not replace it with `dict(row)`, arbitrary mapping methods, or string conversion on unknown objects.

Native arena reads used here are prepaid: `_Family.run` returns arena-resident Records; `_Node.items/scalar/sequence` take arena tables and `_Arena.equal` compares precompiled structure classes. Non-native branches can allocate/charge ledger and must not enter the pure route. Python invocation-local lists/iterators still allocate; “no new arena/ledger charge” does not mean zero allocation.

## Error-order and cleanup constraint

Moving the entry content pin past the collector changes mixed-error priority unless explicitly preserved. Example: mutate an unused CGR root and also corrupt an Approval's typed field. The old entry pin rejects root drift before the typed error; a naive dynamic → collector → exit pin reports the typed error and never reaches the full check.

A failure-only complete pin before propagation can preserve that priority only while original graph/mode state remains intact and before `_base`'s invalidation. Do not add a `finally` check that replaces arbitrary exceptions. In particular, `_Family._root` → `_AccountedScope._current` (`cold_accounted.py:222`) closes its owner on dynamic failure: a late full check after that close merely reports closed mode and cannot reconstruct the original priority. Qualification/collection must not trigger such closing side effects before the fallback/full-boundary decision, or that input must take the original path. An exact implementation must show this explicitly; merely counting fewer codecs is insufficient.

## Concrete finite counterexamples for the patch review

1. Unused complete-root drift plus typed-storage mismatch: original rejection order and sticky invalidation remain correct.
2. A foreign root key whose hash collides with a requested name and whose equality mutates inputs/records a callback: qualification invokes neither callback; legacy full boundary precedes dispatch or original rejection.
3. Root standard model containing a nested Any BranchCondition with a modified serializer that mutates raw to match its output: no fast-path invocation of that callback; original snapshot bridge retained.
4. Same SchemaSerializer type with a new schema, or in-place schema hook change with the same schema identity: legacy selection before execution.
5. Unknown late actual/raw value, raw cycle, shared DAG matched to different actual values, and omitted-None wrong key: original complete gates/comparison order retained; no successful publication.
6. Stop/settings/registry/owner change at the final typed boundary, or closed connection: cheap endpoint witnesses and cleanup still reject; no guard/data equality result escapes across calls.

These are local source/unit obligations. The authorized configured complete semantic A/B remains the actual integration oracle; it must retain original prepare, both commits, receipts, normal scope return, all negative cases, full SQL/output equality and disclosed virtual-clock limits. No new real-time G0 window or performance claim follows from this design review.
