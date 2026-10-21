# Receipt candidate: single-window result review

**Confirmed result: UNKNOWN; original first commit expired; final deadline NOT_PROVEN.** OWNED was issued, but the first `_ColdTrialGraph.commit` did not return. The later original receipt pass and its two new proof roots were not reached. This run therefore does not validate the receipt continuation at runtime, two-commit completion, or complete G0 acceptance.

The reviewer read original logs/JSON/JSONL, source and hashes only. No tests, DB connection/query or DB-file inspection, product, Mock/model, G0, profile or signals were executed; no source or repository file was changed; no grant/window was created. A read-only process listing separately found no surviving launcher PID 51568, child PID 51592 or member of its owned PGID 51592. Child handle cleanup is evidenced by its own marker, not retrospective handle-by-handle inspection.

Run root: `/tmp/sim2act-authorized-receipt-g0-1d84330347f74f3ba56ff88ee2195995/runs/receipt-g0-1d84330347f74f3ba56ff88ee2195995/`.

Execution/current checked HEAD is `5a012556196271c5b33137a1d0b9b4864c64784c`; working tree was clean at the read-only audit. The description/grant and child before/after/parent post-cleanup consistently record source digest `1c12ad8aaeaaaf41c635863275f6c154a5b2d5b4f826da65b91e522a2624de91`. Eight relevant current source files were independently hashed and matched the saved manifest, including the reviewed receipt/native/runtime/apps sources and unchanged launcher/guard/prefix. This is not an independent whole-environment manifest recomputation. Candidate profile remains `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`.

Invocation and separately saved observed parent argv use the absolute launcher path and this exact consumed grant. One run directory and the zero-byte consumption marker are present. Supplied evidence contains no retry. The grant retains six exchanges/eight method entries, prefix 480s, G0 supervisor 120s, total work 600s, cleanup 5+5s and 64 MiB sampled directory budget. These supervisor budgets do not replace the original lease or other finite gates.

The diagnostic's final record reports **6 Mock exchanges / 8 method entries / 2 Source delegates**. The wire archive independently has six completed status-200 synthetic Mock transport records. No real-model or production-account qualification follows from this isolated fixture. Control records show a single G0 entry after the expected Generate/Source/extraction prefix.

The candidate has one commit record, ordinal 1, `returned=false`, `error_type=DomainError`, no successful commit deadlines; no second commit entry, no normal original-context return and `final_deadline_check=NOT_PROVEN`. The original error is `VERSION_CONFLICT: Production admission expired during verification`, traced to the existing `commit` finite gate. Its complete original diagnostic records:

- Lease/run-check deadline `1792580404.8569577`.
- Final sampled `end=1792580405.388139`, `stop=false`.
- Direct `end - lease = 0.5311813354492188` seconds.
- Other reported finite deadlines are later; the minimum is the lease/run-check deadline. The earlier run-context sample was `1792580398.1483963`.

That direct timestamp difference measures this particular gate's sampled lateness. G0 wall duration `30.576640528997814` seconds and total supervised work `341.7464095940013` seconds have different bases; subtracting 30 from G0 wall is not the measured lease overrun, and total work is not G0 time. The raw selected-path classification remains conservative `UNKNOWN` with `UNDETERMINED_ORIGINAL_OR_CANDIDATE`; source/diagnostic localization establishes which original finite gate rejected without relabeling that raw result. Parent reports launcher exit 2, consistent with the frozen launcher's explicit UNKNOWN-to-2 return; this review did not independently capture its original process exit status.

In the unchanged original `advance_model` sequence, `_cold_receipts` occurs only after first commit returns. Since the first commit raised, the new runtime begin/binding-root/produced/proof-root/finish sequence did not execute. Pre-issuance qualification/preload/budget can have completed to obtain OWNED; that is a different claim from receipt proof registration. Cold2 and W5 were not reached. W5 absence follows the static stopped source position and boundary design, not an observed W5 counter. `_ColdTrialGraph.commit` is a validation helper; no enclosing SQLite transaction commit is inferred.

Logical accounting reports issuance resident/live **458430612**, peak **478097556**, work **188404034025305936651508**, below the unchanged explicit logical caps. It reports no capacity refusal. After scope unwind resident/live are zero and active is false. These are conservative reservations and fuel, including prepayment; they are not measured RSS, actual live heap, GC release, elapsed/CPU limits, or universal input qualification. The documented original SQL decode/materialization and full guard/codec baseline exclusions still apply.

Directory monitoring records **6785 samples**, peak logical **2262825** bytes and allocated **2277376** bytes, below 67108864 bytes. It expressly reports sampled budget, not hard quota: `.1` configured interval is not scheduled; policy is every supervisor iteration/finalization with selector cap `.05`, and maximum observed sample completion gap is about `.160` seconds. It does not establish between-sample peaks or a process RSS bound.

G0 authorizer denials are zero. Child final cleanup is `THREADS_CLIENTS_CONNECTIONS_CLOSED`; parent cleanup is `OWNED_GROUP_EMPTY`, with an empty finalization-errors list and unchanged source digest. These cleanup/limit observations support correct termination under the original bounded contract, not business or performance acceptance. No gate was removed or budget expanded in this review; no subsequent attempt is approved.

Original-file SHA-256 bindings:

| Artifact | SHA-256 |
| --- | --- |
| receipt.json | e1ed3926fc8f6ab65b148878f689e0c2da66f92045d316a3c86ca2a443a08a64 |
| diagnostic.json (pre-cleanup and child-final records) | a7c753f15e96800b7ef722da7c68ba6ce1695b78d9bb4de6dace8d5ff593efbc |
| control.jsonl | cf05f28507baa1d611e6e8c63c67775a9a34c422528b4522a77f1f983ec38376 |
| mock-exchanges.jsonl | 2fd47be75658736744d95b518921c1350b5799be50c2fa256e3c56007b685f22 |
| prefix-proof.json | 5973ee954043eb9798f83cf878e05e68c26c4237983a9d762a1997671ea61faa |
| source-manifest.json file bytes | c6b641f97ccfc72faf8f27ab3d8415238d0df31a1c5240cfb47ed6affc480f0e |
| parent description.json | 378632085f9a7292f43b512d2746b27633099f52cd138f3b95d53d1a0f82cb8a |
| parent grant.json | 8b129d419164fa4540d5d037c4052d7bd819272634d727aa113c71b58d177a2e |
| parent invocation.json | e9f3027cbd20bc6b4fba5b366021e0130532bc584c12ce3d31aaafa2e428f038 |
| parent parent-argv-observed.json | 94d3177143acd3f4948fcce97c9f43ed39d60c763d197ea08b4ae1d61dea542c |

The DB hash in the parent receipt remains an author-recorded byte binding; no database semantics or final row counts were independently checked here.
