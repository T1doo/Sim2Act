# Accounted representation prototype — independent static review

Decision: **ACK_OFFLINE_REPRESENTATION_COMPONENT_ONLY / NOT_READY_RUNTIME**.

No remaining blocker was found for the narrow offline representation conclusions below after the surrogate correction. This is not an issued proof, a producer/accounting validator, a compatible consumer implementation, a performance result, or approval to remove/skip any runtime check. The existing bounded-family consumer review remains applicable.

## Frozen inputs and actual audit scope

Reviewed `/tmp/sim2act-accounted-proof-20261021/` code and original logs, including the failed first/diagnostic runs, successful ten-case run retained as `PYTEST-BEFORE-UNICODE.txt`, preserved pre-fix freezer, unicode failure, final eleven-case log, tripwire records and DAG measurements.

Final source bindings:

| File | SHA-256 |
| --- | --- |
| `owned_graph.py` | `3edd9f7eb9c1e21755fcf3cb0333a74aa137025b293998009cc309aed9c4c9a5` |
| `accounted.py` | `92692ce331a510c4012d5a4dd04ec5fcd68e00915e782800ba688524db5ad17e` |
| `test_accounted.py` | `41914caa1e23ff7f28cbc4cef9ca36b0879f941a351e5986b56e3bf92293207a` |
| `conftest.py` | `048ba33d524e86a2fa2ad858e698f30e12b4fcb9f63739e9b153feefc454c5b0` |
| `PYTEST-FINAL.txt` | `32e2dc36bf168ceb5bacffb9e62fdb1719a27930cdd94df656bdd3c4ae6d7a16` |

This reviewer performed source/log reads and report writes only. No tests, prototype execution, product import, profile, DB open/decompression, fixture, Mock/model, G0/launcher, signals or repository writes. Final test counts below are observed parent-run log results, not an independent rerun. Repository HEAD remained `f814843a1ce776c8cdc6387352650b743f8ca0d2`; the parent began adding its untracked evidence directory during this review.

## What is supported

1. **Returned ownership for successful `freeze`.** The returned Packet contains only tuple/NamedTuple structure and exact immutable leaf values. Mutable dict/list/RowMapping storage is traversed into node references; no original mutable container, model or local builder is returned. Immutable bytes/strings may safely be shared. `done` retains sources only inside the freeze call, so it cannot escape in the result or silently reuse a later invocation. The recursive immutable-object test supports the static argument; an unchanged `packet.encoded` alone would not prove ownership.
2. **Cycle and completed-node discipline.** Exact admissible type is checked before memo access; `active` is checked before `done`; nodes are published to done only after all children complete. A self/backedge is rejected rather than emitted as a completed reference. Keeping `(original,index)` in done prevents object-id reuse during that call. Exceptions abandon the local incomplete table instead of returning a partial packet.
3. **Shared longest-path depth.** Each completed node records subtree height. Reaching the same node by a deeper path checks `depth + height` against the bound; it does not inherit the first shallow path's acceptance. The recorded regression tests the shared-path distinction at bounds four/five. Node and edge checks count actual represented nodes/outgoing edges, not recursively expanded paths.
4. **DAG encoding does not expand path multiplicity.** Children are integer references in a flat immutable node table. The supplied repeated-sharing sample moves from 8 nodes/7 edges/183 encoded bytes at depth zero to 48 nodes/87 edges/852 bytes at depth forty. This is a representation-size sample, not a timing benchmark or a G0 estimate. Complexity descriptions must include payload bytes and reference encoding width; the sample demonstrates absence of exponential path expansion, not a universal runtime bound or throughput claim.
5. **Complete bounded family views.** The adapter checks full current `runs/attempts` column sets; preserves the full chains/NS shapes and all three/two counts; validates actual nested model storage with the existing fixed trusted helpers before using fixed class dumps; and freezes complete parsed/checked/byte data. Full row keys/data/safe-index payloads are separately retained as owned sidecars. Business views normalize trusted quoted column names to exact strings, keeping original key tags/storage in the sidecar. This correctly distinguishes business projection compatibility from identical old raw-layout bytes.
6. **Limited legacy mapping evidence.** Tests compare complete projected values after the existing controlled key normalization and compare old Slot/Capture/BodyArchive and CAPTURE-request identity fingerprints on the supplied values. Raw request/payload hashes, BodyArchive anchor fingerprints and public receipt field derivation are also checked. Type tags preserve int/bool/float, signed zero and list/tuple distinctions. Local sharing may change the private digest while materialized business fingerprint values stay equal. Private packet tags/node ids are not substituted into persistent fingerprint algorithms.
7. **Cross-call freshness and external mutation isolation.** Tests mutate every represented aid's nested identity/outcome/capture/parsed/checked data, Source archive fields and Run context. Already frozen structure stays owned; a fresh capture observes a different complete snapshot. Unknown objects/model storage drift and unsafe view keys are rejected without the tested foreign callbacks. The extra-field/missing-field/count/cycle/hidden-row cases are meaningful representation counterexamples.

## Concrete issue found and resolved

The reviewed initial freezer used strict `text.encode('utf-8')` for leaf accounting. Existing `strict_json` accepts ASCII JSON escaped lone surrogate strings, `response_archive` can preserve them with `ensure_ascii=True`, and the existing C Pickler accepts them. This was a real data-domain mismatch, not a hypothetical monkeypatch-order objection.

The parent added a regression that first proves the existing `_cold_graph_bytes(value)` accepts the parsed value, then exercises the freezer and a Source parsed-response field. `PYTEST-UNICODE-BEFORE-FIX.txt` records the actual `UnicodeEncodeError`; `owned_graph.before-unicode.py` preserves the earlier freezer SHA `fe96c52e5d75bfa227f2c40bb1936d219113f7db13a69423a9dbfe19214bd1b9`. The final freezer counts with `errors='surrogatepass'`; its actual private encoding remains escaped ASCII JSON. The final logged eleven-case pass covers the new high/low-surrogate example and response-archive mapping. This corrects the identified domain narrowing without changing production code or existing raw wire bytes.

Earlier failures were also retained accurately: first run 3 failed/7 passed; diagnostic run 2 failed/1 passed/7 deselected. The quoted-name mismatch was resolved by testing the controlled business projection separately from preserved raw-storage sidecars. The direct assignment to a frozen model was changed to an explicit `__dict__` mutation to exercise the intended drift case. These are not erased failed business runs.

## What is not proved or implemented

* **No issuer or capability.** Packet/View are publicly constructible and may be forged with inconsistent digest/nodes/bodies. `resolve` does not authenticate them. The adapter deliberately captures swapped chains and invalid/unknown semantic facts; shape/count checks do not prove aid/run/slot/ledger/archive association or semantic validity. There is no scope/connection/transaction/role issuance mechanism. This is an accurately disclosed limitation of the component, not a safe runtime admission path.
* **No producer equivalence.** Full synthetic standalone rows and real model classes reuse archived third-window Mock exchange bytes. They are not recovered actual authorized Runs, a complete valid production ledger or the original G0 graph. Their MOCK/default synthetic Capture/constructed Outcome values do not qualify `_graph_stage_accounted`, its current permissions, seals/anchors, Operation SELECTs or all policy joins.
* **Current consumers remain raw.** The old leaf checks in these tests use detached `materialize_oracle` values and original typed Slot/Capture/BodyArchive objects. They do not run the current consumers solely through View and do not establish complete Stage/Source/archive-chain equivalence. Materialization is explicitly a test oracle and must not become an unnoticed mutable fallback on the runtime path. View has no full typed-model or value-equality contract for those old leaves.
* **Fingerprint coverage is bounded.** Sample equality is not closure of every persistent software/audit/source/approval/receipt chain or mode. The complete-family/root occurrence map, final manifest/pin, pre/post selection and post_graph/origin bridge remain unimplemented. Raw/canonical byte checks, existing business hashes and authorization cannot be replaced by `packet.digest`.
* **Budget mapping is unresolved.** Bounds are explicit proof-input limits only. The complete accepted family scale, producer limits, shared DAG admission, conversion/encoding allocation peaks and runtime memory/time/depth policy need a separate exact mapping. The prototype's handling of bounded samples is not a native memory hard limit or proof that every original admissible input fits. Primitive acceptance must not be advertised as qualification of all possible Python scalar magnitudes/graphs.
* **No dynamic freshness/atomicity evidence.** Current Grant/approval/Run/version/fence/stop/time/source resolver/key-set/Operation reads, non-pure boundaries, W5/postwrite/live/tail and rollback are not tested here. They remain original gateways; neither this snapshot nor its digest grants permission or extends any cap. No fourth business window is authorized.

## Logs and monitoring limits

`PYTEST-FINAL.txt` records CPython 3.12.14 / pytest 9.0.2, 11 collected, 11 passed in 0.40s. This elapsed time is test-suite execution, not a serialization benchmark or expected G0 saving. The successful ten-case predecessor remains separately saved. Tripwire records show zero monitored blocked attempts, with exit status 1 for retained failures and 0 for successful runs. The fixture explicitly activates after pure module imports, for setup/body/teardown; it is not a blanket proof of import-time isolation or a general malicious-code sandbox. The report does not claim otherwise.

The representation component therefore supports continuing a bounded design investigation. It does not justify reducing the current mutable frontier until every listed consumer uses authenticated owned values and the still-open runtime conditions are independently closed.
