# Composite parent pin: single-window result review

**Result confirmed: UNKNOWN / final deadline NOT_PROVEN.** OWNED was selected and the first original commit returned. The next original lazy receipt-binding pin was rejected by the candidate's continuation-root gate before the second commit. This is neither complete G0 acceptance nor a successful two-commit/final-context deadline result. No further execution is authorized or performed by this review.

The reviewer read original JSON/JSONL/logs, source and hashes only. No test, product, DB connection/query, Mock, model, G0, prepare/commit or signal was executed; no repository file was changed and no grant was created. The SQLite file was not opened or independently inspected. A read-only process listing also found no surviving launcher PID 45032, child PID/PGID 45056, or member of that owned group. Child resource closure is supported by its recorded cleanup marker, not a retrospective inspection of its individual handles.

## Execution and exact evidence

Root: `/tmp/sim2act-authorized-composite-g0-59ed1f1cfba542958a5e1f5c67a7e7ec`.

Execution HEAD and current checked HEAD: `ef040cfc780d37d4442327231d21ab500b97a661`. Recorded source digest is `dac37ef4adfd9832653ab9ed61d8a131117edcc3bcf17246a2f9e871661f397c`, identical in description/grant, child before/after, and parent post-cleanup. Eight relevant launcher/guard/prefix/runtime/native/composite source files were independently hashed and match the saved source manifest. This is not a new independent whole-environment manifest computation. The checked working tree was clean at the source audit.

The candidate profile remains `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`. Invocation and separately captured parent argv both use the absolute launcher path `/workspace/Sim2Act/scripts/diagnostics/g0_bounded.py`, `--candidate`, and this one exact grant. The zero-byte consumed marker exists. There is one run directory and no retry in the supplied evidence. The grant retains 6 exchanges / 8 method entries, 480-second prefix, 120-second G0 supervisor budget, 600-second work budget, 5+5 seconds cleanup, and 64 MiB sampled directory monitoring. None is a replacement for the original lease/authorization gates.

## Observed outcome and limits of timing

The control stream contains one G0 entry after Generate, Source and extraction. Child final evidence records 6 Mock exchanges, 8 method entries and 2 Source delegates; the exchange archive independently contains six completed status-200 records classified as synthetic Mock transport, not real HTTP. The original isolated fixture/network-denial design supplies the no-real-model boundary; the final diagnostic does not independently count real-model calls.

Candidate records contain exactly one commit, ordinal 1, `returned=true`, with successful original authority-record deadlines. Here commit means `_ColdTrialGraph.commit`, not proof that the enclosing SQLite transaction committed. The earliest recorded deadline is `1792577691.65724`, also the captured lease deadline. The recorded run-context check time is `1792577684.4134684`. There is **no first-commit return timestamp**, no second commit entry, no normal original-context return, and no final deadlines. The successful original commit entails reaching its existing internal finite/deadline assertion; it does not timestamp its later return. This evidence therefore cannot establish first return within lease or completion of the overall final deadline.

G0 wall time is `30.078201882999565` seconds; total supervised work is `341.4612587740012` seconds. The selected original rejection diagnostic is `NOT_REACHED` and provides no final rejection `end` time. Subtracting 30 from G0 duration is **not** a measured lease overrun: these durations and the lease have different start/basis and the failure is a continuation gate. The whole work duration must not be called G0 time.

The error chain localizes `advance_model -> _cold_receipts -> _ColdRunFacts.pin_receipt_binding -> _put -> _ColdGraphRead.add -> _Frontier.added -> require`, with `DomainError / VERSION_CONFLICT / Unexpected native continuation root`. Source shows this is an original lazy read-position pin that the candidate's finite allowlist did not admit. Source derives a key of form `run-facts:<job id>:receipt-binding:<len receipt proofs>`; the actual key and index were not recorded, so this review does not claim that `:0` was observed. The receipt keeps the conservative selected-path error origin `UNDETERMINED_ORIGINAL_OR_CANDIDATE`, and classification `UNKNOWN` is appropriate. This is not an unmodified original lease refusal.

The second commit, Cold2 and W5 were not reached. For W5 this is established from the stopped source position and boundary design, not a measured W5 counter; the diagnostic expressly labels that basis. No successful final scope return is inferred.

## Resources, cleanup and observation

The route was OWNED with logical peak `105470324`, issuance resident/live `85803380`, and logical work `50098473668149788430366`. After scope unwind, resident/live are zero and active is false. No capacity refusal is reported. These are the candidate's logical accounting units, excluding the documented baseline operations; they are not CPU limits, RSS, or proof of qualification for all inputs.

Disk evidence reports 6778 samples, peak logical `2257144` bytes and allocated `2273280` bytes. It honestly identifies a sampled budget rather than a native hard quota: configured `.1` is not scheduled; sampling occurs every supervisor iteration/finalization, selector cap `.05`, maximum observed completion interval about `.158` seconds. The observed peak is below 64 MiB and does not prove every between-sample state or RSS stayed bounded.

G0 authorizer denials are zero. Child final marker is `THREADS_CLIENTS_CONNECTIONS_CLOSED`; parent receipt is `OWNED_GROUP_EMPTY` with an empty finalization-errors list and unchanged post-cleanup source digest. This supports the reported owned cleanup; it is not a business success. No cleanup gate, continuation gate, lease or safety budget was removed to obtain the result.

The complete stage observer records codec calls 892 in run-context and 1143 in resolver, versus 1510 and 2325 in the prior saved absolute-path attempt. These are observations across two instrumented runs, not a general performance promise. Their current sum is 2035 calls / `5.814263863` thread CPU seconds. All five stages sum to 5729 calls / `15.395801711` thread CPU seconds / `3989501290` returned bytes. Resolver diagnostic `check_calls=1142` and codec calls 1143 are distinct counters. Returned codec bytes are not a measured SHA counter. Observer overhead is nonzero; these values do not prove uninstrumented speedup or remaining deadline margin.

The remaining blocker is the candidate's incomplete normal continuation domain and its corresponding bounded allocation/work/mirror coverage. Any next proposal must cover actual producer roots and their data-dependent construction before admitting them, retain the original lazy SQL/read positions and full fresh validation, and reject unexpected roots. This report approves no wildcard, gate deletion, empirical budget enlargement, source change, or further window.

## Original-file bindings

| File | SHA-256 |
| --- | --- |
| receipt.json (run directory) | 677cfd70def0028f602345c340acfbb55847bfc1b0041e1cbf399a39d775443e |
| diagnostic.json (two JSON records) | 97553c4bad00d86a99f34b90412e69baadc8b16262fc47685797e1ff3fd034f4 |
| control.jsonl | a0db59d48dbb011540a1c50cc087cedbf608c44be0db147d2188358c9a7037a2 |
| mock-exchanges.jsonl | 7d9c35d53499b056c8e757feda9e56f3324eb20ea7828c9c1b656ebab4bc4c95 |
| description.json | 967b2cf598fff3cced03a096697d2525502c45353489f6e5df96b25e00c27a86 |
| grant.json | ebaab2c63785276ef636d88fe749ad2e3617ee0e944574d31f368094bb5b5549 |
| invocation.json | 2ca9ff709fe6f2ff4d32e49f67c510474afc2e6c22892d83abc5a8b0b47db90b |
| parent-argv-observed.json | f2084d3c2b5123f40a90c4089bd37c276527cc30cf49d602ab47874b0eb25b39 |

The parent's `outcome-analysis.json` was also read and is consistent with these precise limitations. Its original-manifest DB hash is an author-recorded byte binding; no DB semantic verification is supplied by this review.
