# Optional fresh C typed visitor: final limited component ACK

**ACK for the explicitly supplied offline experimental component and its recorded evidence. Runtime substitution remains unqualified and disabled.** This is not an all-domain drop-in, complete-chain, production, G0, performance or execution-window ACK.

Reviewer only read source, logs/JUnit and file hashes; no build, extension import, test, database, Worker, Mock, profiler or G0 execution, no repository edits or signals.

Final SHA256 personally checked:

| File | SHA256 |
|---|---|
| C implementation | `beb72b4b1428d14d5b767f03e994348c2d4739b7edc8534347b5c415754b5a2e` |
| explicit candidate adapter | `b2d9feb14b34004808c140a8318f7dfbdf2f1105bbb685f53e0ef0d966977a05` |
| build script | `bd8c90beeb28202bd78d5e733a805c98bdfd7e80c5d87b1732c1bc807111dc9c` |
| tests | `13a9aa12b327cd8de11e3e84c5d5094875903923d3a9e41db7d89920cfeb9644` |

The inspected final C implementation uses strong public builtin descriptor retrieval with NULL checks, exact types, fresh active/seen maps, active-before-seen, real iterators with held references, original metadata evaluation/short-circuit order, and original omission points. The foreign omission-key comparison now uses an interned original identifier literal and Python rich comparison; its identity-sensitive test closes the earlier narrow issue. Error fetching/restoration and owned reference transfers, including `Py_SETREF` on tuple conversion, show no remaining concrete double-free/NULL/error-propagation defect in this static review. This is not a formal memory-safety proof.

The earlier direct-builtin-tp_dict version actually segfaulted, as reported and diagnosed by the author; it is not treated as a successful run. The final public-API fix and prior reviewer history remain distinct. Default `natural_live_admission`, runtime and base guard have no source diff; neither automatic backend discovery nor a production route selects this component. Unknown helper identity takes Python before native work, and native errors do not retry through Python.

Read author evidence:

- Final ordinary selection: **32 passed / 5.44s**, including four native versions of the original counterexamples plus four original Python tests, actual prepared-PB key/container alias bytes, full original codec envelope with hidden RowMapping storage, exact types/DAG/omissions, metadata ordering and descriptor exception identity, iterator mutation, raw ABI rejection, signal exception identity and cleanup/deep cases.
- Earlier debug-allocator/dev run: **31 passed / 5.81s** on the earlier test selection without the final RowMapping case; not relabeled as all 32 final tests.
- Same final source under the author's extension-only ASAN build: **32 passed / 6.47s**, no ASAN memory-access report in the log. The author specifies `-O1 -g -fsanitize=address -fno-omit-frame-pointer`, existing libasan preloaded, `detect_leaks=0`. This is not whole-interpreter instrumentation or LSan/leak freedom. The final ordinary and ASAN runs exercise overlapping cases, not 64 distinct tests.

The ordinary component cost test uses the actual prepared PB contract, a fresh typed copy plus unchanged C pickle on every iteration, no profiler, 1,000 calls per sample. Python seconds are **0.127002868 / 0.124587116 / 0.119987135**; C seconds **0.058049864 / 0.059969367 / 0.058258495**. They support a local opportunity on this contract only. Fixed Python-then-C timing order, three samples and a single component do not establish full-tail improvement, general workload speedup, RSS/lease benefit or a fraction of the old 8,086 calls / 16.96 cumulative profile seconds. ASAN/debug timings are not the normal performance samples.

## Explicit unresolved runtime qualification

The final tests intentionally establish a behavioral difference: a 1,500-deep input raises Python RecursionError but the native visitor returns; at 20,000 depth the native recursion guard rejects. This proves a native recursion guard exists, **not** that its threshold or error ordering equals Python/generator recursion. Therefore all-domain `_trial_typed_storage` substitution is currently blocked. No small new business depth cap, GIL immutability claim or presumed production qualification is supplied.

A further complete semantic chain is **not necessary for the current declared offline component delivery**, and a shallow successful chain would not close this known deep-input difference. Before using a chain as substitution evidence, its exact bounded input domain, ABI/backend qualification and actual call-site routing would need to be explicit. Globally replacing `gate._trial_typed_storage` would also invalidate the existing base helper-identity witness and can force legacy routing, so such a test must not be advertised as unchanged native candidate eligibility. No new harness, source route, Mock or runtime window is requested here.

Current disposition: keep default Python/product routes; preserve the optional native primitive, positive local evidence, initial failure history and explicit recursion counterexample. No additional concrete P1/P2 was found for that limited unenabled component scope. This does not approve activation or deny that a later specifically qualified route might be feasible.

Evidence SHA256:

- normal log `d79b98776c29dc14c609fea4be142129b5787b870a2b063b93546a95c62fce95`
- normal JUnit `d5675b08aefd8f27b4761defdeb2cacd2c641d6d7ac6f7f08f9bc3dcec0f5476`
- ASAN log `6e62df8d83e0e2a61519d3e9747352b9ff6911bf075ecc082453a0b666316965`
- ASAN JUnit `3d6e0949cd9fe1a0d7f25c7031c1d5d8278a0c2305dd8c0c54207e3895f036cf`
