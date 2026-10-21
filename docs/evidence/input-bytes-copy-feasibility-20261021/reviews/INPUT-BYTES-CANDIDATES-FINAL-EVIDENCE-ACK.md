# Input-bytes candidates: limited evidence ACK

Baseline HEAD independently read: **`b9a6bfaad5212c0a8f799975afa4893d613b3308`**. `git diff --stat -- src scripts` was empty; the only repository change observed was the new untracked alias-contract test. No production pool, copy shortcut, new protocol or codec implementation was installed.

Reviewer only read source/logs/JSON and official CPython source, and hashed files. Reviewer executed no product imports, tests, database access, Mock, Worker, profiler or G0. This ACK approves the bounded findings/stop conclusion, not a replacement implementation or new execution window.

## Actual source-derived negative witnesses

`tests/test_cold_typed_storage_alias_contract.py` SHA256 **`ac1182eeb2c216006c7822f9b6e7ac987e06d672ad4922ff2f9c3838e0b8c15e`** uses an actual `prepare_pb` PBTrialContract, original `_trial_typed_storage` and original C pickle codec. Existing execution tripwires forbid Worker/model/HTTP/Mock. The log records **3 passed / 1.36s**.

- Retained equal keys: a newly constructed equal-but-distinct accepted native string key is retained by the fresh projection and shared with crafted graph input. Updating a previous projection preserves the old key instead. Typed value equality/order still match, but complete codec bytes differ, demonstrating the lost memo alias.
- Copy-before-traversal: deterministic mutation between the proposed shallow copy and its iterator changes current `quota_subject`. Full original fresh projection sees the new scalar; conditional `visited is not child` patching retains the old scalar and exactly reproduces the old projection bytes. This is a deterministic representation/interleaving witness, not an executed concurrent-thread test or a successful authorization flow.
- Unconditional value patch: moving/replacing one key with an equal different string changes accepted native key identity/order; patching values into the prior copy preserves the old key/order. Original fresh projection and old-key copy again produce distinct complete codec bytes.

These establish current projection freshness, separation and key-alias obligations. They do not depend on arbitrary serializer monkeypatches, prove full G0 behavior, or prove every possible pooling strategy impossible. The test envelope intentionally exposes the alias with a crafted small input rather than pretending to be an archived full G0 graph.

## Limited destination-buffer experiments

Standalone `/tmp/.../test_buffer_proof.py` SHA256 **`74fb846cd9af436f7d28b457bb5f471105b4fa877af59babfa8f0358e817ad76`** retains original C Pickler/protocol 5/fresh memo. It uses a private stream, rewrites the same envelope, truncates before getvalue, and checks exact bytes and held returned bytes. It is an unqualified offline prototype, not a production thread-local pool.

| Input | Author pass log | Work per alternating-order round | Fresh CPU median | Buffer CPU median |
|---|---|---:|---:|---:|
| Actual prepared PB contract projection, 4,311 bytes | 1 passed / 1.16s | 2,000 encode+SHA256, 6 rounds | 0.0150812345s | 0.015092861s |
| Closed synthetic SQL snapshot, 225 rows / 736,577 bytes | 1 passed / 1.92s | 50 encode+SHA256, 6 rounds | 0.121059195s | 0.120183769s |

The contract projection is constructed once outside this timer; the experiment isolates destination reuse rather than timing fresh typed projection. There is no meaningful improvement in that sample. The row snapshot difference is approximately **0.7231%**, without real resource-qualification, lifecycle or thread-local management overhead and without statistical inference. Row size similarity does not make its shape the actual G0 input graph. No overall tail, G0, CPU/RSS improvement or production benefit follows.

The snapshot test opens an existing closed synthetic DB with SQLite URI `mode=ro`, disposes the engine, and asserts whole-file SHA256 unchanged; the passing log supports that author-run assertion. Reviewer did not open the database. Its recorded SHA256 is `0d65862f50aa545fb93aa31e15d3f78c74bcca09e57976c3b65e0b04d1fc6b36`. The test has no new model exchanges, and no new full chain was executed for this slice.

## Conclusion and smallest technical direction

The evidence supports retaining the original production implementation: the assessed typed-copy shortcuts have concrete contract counterexamples; the qualified destination resource pool has no demonstrated sufficient benefit from these limited samples. There is no reason in this evidence to spend another complete-chain run or expand the changes.

The original per-call seen map already clones each first-visited logical typed projection node once and preserves its internal sharing, while keeping the deliberate model/raw projection separation. Eliminating that separation is not merely removing a redundant allocation. CPython exact dict/list/tuple dispatch occurs before `reducer_override`; a Python virtual mapping/reducer is therefore not a drop-in identical-wire projection of those native objects. See [CPython 3.12.14 `_pickle.c`, save dispatch and native container paths](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_pickle.c).

A native **fresh typed-projection visitor** that still returns the original native clone graph to the unchanged C Pickler is one concrete further technical direction. It would require a separate implementation/proof of exact type/key/header/DFS/schema-read/error semantics, active/seen ownership and aliases/omissions, plus ABI/build qualification. It is not already implemented, guaranteed faster, the uniquely minimal solution, or authorized by this ACK. Rewriting the C Pickler or changing the protocol is unnecessary to describe that direction. This limited rejection does not claim all future optimization impossible.

Raw evidence hashes:

- alias log: `88120659a22a5c9003d1cf531f024c7509156f2eb6ea941e443fdc77d70d6ff7`
- contract buffer log: `2427bc0264fdd4d4d2cc859372cd79f8d6c7f679b0983cf62e7725c6b1dfcd77`
- row buffer log: `ec4195625956ee179250e90c20ef8bc7d64a27e7524349ff456c4fe6af059adf`
- contract costs: `07331a88a1bb8939766364148825c97c9a25803ff2b1bd71ae317d6e460adda0`
- row costs: `34fc17185b6423ac9696542e1846f6443802559839a94be1ace9441cc7eba486`
