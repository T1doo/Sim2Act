# Codec source and fixed-six Limits candidate review

**Decision: NO_GO_IMPLEMENTATION / NO_NEW_BENCHMARK / NO_FOURTH_WINDOW.** Reject the literal-form proposal under the strict callback requirement; retain its rejected design record and do not apply it. There is both a strict observable-call problem with this literal form and insufficient value evidence. No new production candidate is ACKed.

Baseline HEAD: `ec9cf8f936427e64f0a07e2fc30f498076f05376`. Runtime/admission source hashes are unchanged and recorded in REVIEW.json. Work was limited to source and saved-result inspection, reading existing pstats, official-source retrieval, and writing /tmp review files. No test, profile, microbenchmark, DB, fixture, model/Mock, G0 or launcher was run.

## The specific operation

The proposal changes only the final return in _cold_graph_limit_values from a tuple constructor consuming a generator over six names to six explicitly ordered literal-key pairs. Its preceding raw/keys/extra/private/type require remains unchanged. It does not remove a pin or fresh dictionary read and is not the previously tried type-dispatch change.

Under fixed ordinary module/builtin bindings, the six dictionary reads can retain their order and return the same original integer object references. The six field-pair tuples and outer tuple remain fresh. The field strings are ASCII identifier-like literals; CPython 3.12.14 recursively interns such constants, including those inside tuple constants, so the direct literals can retain the original names-element identity. This supports a conditional normal-data identity/alias argument, not an already-tested whole-codec proof. See [CPython codeobject.c](https://raw.githubusercontent.com/python/cpython/v3.12.14/Objects/codeobject.c), all_name_chars/intern_string_constants.

**The literal form is not strictly callback-equivalent.** Original code dynamically resolves and calls tuple at this location; a tuple literal removes that resolution and call. A static counterexample follows an already-established callback edge:

1. Encode a native RowMapping followed by a valid exact Limits.
2. The first row's storage validation finishes before its marker global is saved. The existing marker-import hook can then set runtime.tuple to a callable which raises a chosen original exception object.
3. The subsequent Limits helper's unchanged require uses dict/str/set/int/all checks and does not read tuple.
4. The original return resolves/calls the new tuple binding and raises that exception object. The literal return bypasses it and can complete.

This is grounded in the existing test_shared_row_metadata_is_reread_after_pickle_global_import_callback source, which documents the same row-to-next-reducer import boundary. The counterexample was **not executed**. Preserving six data reads does not preserve a removed observable call. Generator tracing/resumption and allocation-failure timing also differ, but the module-binding counterexample is stronger and sufficient; no speculative tracing assumption is needed.

## What the native implementation rules out

CPython 3.12.14 already performs native primitive handling and memo lookup before the custom reducer path, caches the bound reducer once per dump, and flushes frames through the saved write callable. Its 64KiB frame target and large-payload bypass are internal; the direct internal string getter is not a public subclass API. These facts do not expose a redundant method lookup or a supported zero-copy replacement for this application. [CPython _pickle.c](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_pickle.c)

BytesIO writes may grow/copy its buffer, while getvalue can resize/share the existing bytes in the unexported case. Therefore returned byte volume does not imply an unconditional extra final full copy to remove. [CPython bytesio.c](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_io/bytesio.c)

Changing reducer dispatch, disabling memo, reusing state, changing output representation or adding streaming callbacks would require different invariants and is outside this proposal. The public API gives reducer_override priority and preserves memo for sharing; it does not offer a drop-in alternative retaining this custom rejection contract and all current bytes/callbacks. [Python Pickler documentation](https://docs.python.org/3.12/library/pickle.html#pickle.Pickler)

The three pinned official sources were independently downloaded into official/; pickle.c and bytesio.c match the parent's source copies exactly. Their hashes, including codeobject.c, are recorded in REVIEW.json. No source was compiled or executed.

## Exact cost ambiguity

Third-window codec aggregate is 5697 calls, 16.319125064 thread CPU seconds and 4,408,544,578 cumulative returned bytes. It includes but does not separate:

- Limits, RowMapping and quoted-name reducers, fresh validation/readout and their temporary payload allocations;
- native primitive traversal, memo operations and opcode emission;
- frame creation/flush, native buffer resize, sink copying/growth, final buffer sharing/resize and marker global/import work.

The four-metric observer did not record actual Limits reducer calls, Limits helper CPU, or the tail-generator subset. A 0.955520630-second wall deadline miss does not identify one of these costs as removable, nor make an unmeasured small change sufficient. There is no demonstrated same-input improvement or remaining safety margin; CPU components and deadline wall time are different quantities.

The saved small profile is specifically a 61657-byte input. Its 100 calls contain 100 Limits helpers with 0.000679291 cumulative cProfile seconds for the **entire helper**, versus 0.023695227 codec cumulative seconds. These use cProfile.Profile()'s default timer and are not the third-window thread_time_ns CPU measurements. The proposed generator is a smaller unknown portion. This sample does not justify a meaningful benefit even within its own narrow shape, and must not be multiplied into current G0.

It also has 4000 row-storage calls and 4200 reducer calls. The 100 explicitly profiled BytesIO.write calls correspond to explicit header writes; C-internal writes remain in dump's residual rather than an isolated pstats cost. The small complete output is below the 64KiB frame target; third-stage mean outputs are approximately 0.67–0.96MB. Means are not size distributions or frame counts. These differences explain exactly why the existing pstats cannot resolve the current native sink/reducer split. Stored-PSTATS-READ.log preserves my read-only extraction; no new profiling occurred.

## The one missing performance input and the allowed path

The missing **performance/representativeness input** is a trusted, reconstructible complete actual codec input graph for the relevant stage states, including full hidden row data/index/metadata, exact model/role-limit values and alias topology. It is not a missing generic observer. The third observer intentionally retained only aggregates and shallow counts. Exchange/contract JSON does not reconstruct the then-growing graph and object identities; the old fingerprint-only complete-input.bin.gz must never be loaded.

If an already-authorized complete specimen existed in a trusted constructor-readable representation, the narrow offline route would be to reconstruct only its controlled native/model objects without DB/Worker/producer, then review a bounded same-input leaf differential/cost check before execution. No such specimen has been identified, and no currently approved operation obtains it from the saved aggregates. Do not substitute a new weak shape, open a business window, restore a DB or build a general fourth observer. Input availability alone would still not repair the dynamic-tuple counterexample.

The final parent DESIGN.md SHA256 is `a5fe56c98a14130ef2598d949a5535a6a0811bc29f750aaa669ae7ac82927c3c`; CODE-FACTS.json SHA256 is `ed9999d45d52867bef74c9bbb19624bed30957b977ede007c26641281ce8e8fd`. Both were read. The corrected design accurately records strict rejection of the literal candidate, the independent callback counterexample, the missing performance specimen, and the separate cProfile/thread-CPU clock bases. It does not imply that more input revives this rejected candidate. Earlier wording corrections are resolved; this design record is accepted, with no implementation or benchmark authorization.

Current disposition is to retain the source unchanged and record this exact rejected/not-ready operation plus the missing input. No class-list, validator, SHA-removal, type-dispatch, prefix, streamed-SHA, cache, pin, transaction or lease direction was retried.

